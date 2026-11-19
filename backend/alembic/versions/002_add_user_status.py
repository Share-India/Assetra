"""Add user status column to users table

Revision ID: 002_add_user_status
Revises: 001_initial_tables
Create Date: 2026-10-19 11:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_user_status'
down_revision = '001_initial_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'status',
            sa.Enum('pending', 'active', 'rejected', 'disabled', name='user_status_enum'),
            server_default='pending',
            nullable=False
        )
    )


def downgrade() -> None:
    op.drop_column('users', 'status')
