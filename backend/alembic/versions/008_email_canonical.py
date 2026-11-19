"""Add email_canonical column and enforce unique indexes on email and email_canonical

Revision ID: 008_email_canonical
Revises: 007_create_audit_logs_table
Create Date: 2026-11-16 18:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = '008_email_canonical'
down_revision = '007_create_audit_logs_table'
branch_labels = None
depends_on = None


def canonicalize_email(email: str) -> str:
    """Normalize and canonicalize an email address."""
    if not email:
        return ""
    clean = email.strip().lower()
    if "@" not in clean:
        return clean
    local_part, domain = clean.rsplit("@", 1)
    if domain in ("gmail.com", "googlemail.com"):
        local_part = local_part.split("+")[0].replace(".", "")
        domain = "gmail.com"
    return f"{local_part}@{domain}"


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_cols = [c['name'] for c in inspector.get_columns('users')]
    existing_indexes = inspector.get_indexes('users')
    existing_index_names = [idx['name'] for idx in existing_indexes]

    # 1. Add email_canonical column if not exists
    if 'email_canonical' not in existing_cols:
        op.add_column('users', sa.Column('email_canonical', sa.String(255), nullable=True))

    # 2. Backfill existing users with normalized email and email_canonical
    users = conn.execute(text("SELECT id, email FROM users")).fetchall()
    for u in users:
        uid = u[0]
        raw_email = u[1] or ""
        email_clean = raw_email.strip().lower()
        canon_email = canonicalize_email(email_clean)
        conn.execute(
            text("UPDATE users SET email = :clean, email_canonical = :canon WHERE id = :uid"),
            {"clean": email_clean, "canon": canon_email, "uid": uid}
        )

    # 3. Alter email_canonical to NOT NULL
    op.alter_column('users', 'email_canonical', existing_type=sa.String(255), nullable=False)

    # 4. Enforce unique index on email_canonical
    if 'uq_users_email_canonical' not in existing_index_names and 'ix_users_email_canonical' not in existing_index_names:
        op.create_index('uq_users_email_canonical', 'users', ['email_canonical'], unique=True)

    # 5. Ensure unique index on email
    has_unique_email = any(
        idx.get('unique') and idx.get('column_names') == ['email']
        for idx in existing_indexes
    )
    if not has_unique_email:
        op.create_index('uq_users_email', 'users', ['email'], unique=True)


def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    existing_cols = [c['name'] for c in inspector.get_columns('users')]

    if 'uq_users_email_canonical' in existing_indexes:
        op.drop_index('uq_users_email_canonical', table_name='users')
    if 'ix_users_email_canonical' in existing_indexes:
        op.drop_index('ix_users_email_canonical', table_name='users')
    if 'email_canonical' in existing_cols:
        op.drop_column('users', 'email_canonical')
