"""Add username, first_name, surname, pending_email to users and user_sessions table

Revision ID: 004_account_settings_upgrade
Revises: 003_public_auth_tables
Create Date: 2026-11-16 00:48:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '004_account_settings_upgrade'
down_revision = '003_public_auth_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_cols = {c['name'] for c in inspector.get_columns('users')}

    if 'username' not in existing_cols:
        op.add_column('users', sa.Column('username', sa.String(length=80), nullable=True))
        op.create_index('ix_users_username', 'users', ['username'], unique=True)
    if 'first_name' not in existing_cols:
        op.add_column('users', sa.Column('first_name', sa.String(length=80), nullable=True))
    if 'surname' not in existing_cols:
        op.add_column('users', sa.Column('surname', sa.String(length=80), nullable=True))
    if 'pending_email' not in existing_cols:
        op.add_column('users', sa.Column('pending_email', sa.String(length=255), nullable=True))

    existing_tables = set(inspector.get_table_names())
    if 'user_sessions' not in existing_tables:
        op.create_table(
            'user_sessions',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('token_hash', sa.String(length=64), nullable=False),
            sa.Column('remember_me', sa.Boolean(), server_default=sa.text('0'), nullable=False),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('last_active_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('revoked_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('token_hash', name='uq_user_sessions_token_hash'),
            mysql_charset='utf8mb4',
            mysql_engine='InnoDB'
        )
        op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'], unique=False)
        op.create_index('ix_user_sessions_token_hash', 'user_sessions', ['token_hash'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_cols = {c['name'] for c in inspector.get_columns('users')}
    if 'pending_email' in existing_cols:
        op.drop_column('users', 'pending_email')
    if 'surname' in existing_cols:
        op.drop_column('users', 'surname')
    if 'first_name' in existing_cols:
        op.drop_column('users', 'first_name')
    if 'username' in existing_cols:
        op.drop_index('ix_users_username', table_name='users')
        op.drop_column('users', 'username')

