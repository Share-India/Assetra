"""add attempts column to password_reset_tokens

Revision ID: 009_password_reset_otp
Revises: 008_email_canonical
Create Date: 2026-11-17 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '009_password_reset_otp'
down_revision = '008_email_canonical'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    cols = [c['name'] for c in inspector.get_columns('password_reset_tokens')]
    if 'attempts' not in cols:
        op.add_column(
            'password_reset_tokens',
            sa.Column('attempts', sa.Integer(), nullable=False, server_default='0')
        )


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    cols = [c['name'] for c in inspector.get_columns('password_reset_tokens')]
    if 'attempts' in cols:
        op.drop_column('password_reset_tokens', 'attempts')
