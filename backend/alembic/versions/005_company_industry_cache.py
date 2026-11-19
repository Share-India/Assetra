"""Add company_industry_cache table

Revision ID: 005_company_industry_cache
Revises: 004_account_settings_upgrade
Create Date: 2026-11-16 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '005_company_industry_cache'
down_revision = '004_account_settings_upgrade'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'company_industry_cache' not in existing_tables:
        op.create_table(
            'company_industry_cache',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('company_hash', sa.CHAR(length=64), nullable=False),
            sa.Column('normalized_name', sa.String(length=255), nullable=False),
            sa.Column('suggested_industries', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('company_hash', name='uq_company_industry_cache_hash'),
            mysql_charset='utf8mb4',
            mysql_engine='InnoDB'
        )
        op.create_index('ix_company_industry_cache_company_hash', 'company_industry_cache', ['company_hash'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'company_industry_cache' in existing_tables:
        op.drop_index('ix_company_industry_cache_company_hash', table_name='company_industry_cache')
        op.drop_table('company_industry_cache')

