"""Create test database far_app_test

Revision ID: 011_create_test_database
Revises: 010_alias_validation_summary
Create Date: 2026-11-17 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '011_create_test_database'
down_revision = '010_alias_validation_summary'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Ensure far_app_test database exists with proper charset and collation
    op.execute("CREATE DATABASE IF NOT EXISTS far_app_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")

def downgrade() -> None:
    op.execute("DROP DATABASE IF EXISTS far_app_test")
