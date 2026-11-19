"""Upgrade column_alias_cache and add user_column_mappings table

Revision ID: 006_column_mapping_upgrade
Revises: 005_company_industry_cache
Create Date: 2026-11-16 02:46:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '006_column_mapping_upgrade'
down_revision = '005_company_industry_cache'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'column_alias_cache' in existing_tables:
        existing_cols = {c['name'] for c in inspector.get_columns('column_alias_cache')}
        if 'original_header' not in existing_cols:
            op.add_column('column_alias_cache', sa.Column('original_header', sa.String(length=255), nullable=True))
        if 'status' not in existing_cols:
            op.add_column('column_alias_cache', sa.Column('status', sa.String(length=30), server_default='approved', nullable=False))
        if 'sample_values' not in existing_cols:
            op.add_column('column_alias_cache', sa.Column('sample_values', sa.JSON(), nullable=True))
        if 'validation_passed' not in existing_cols:
            op.add_column('column_alias_cache', sa.Column('validation_passed', sa.Boolean(), server_default=sa.text('1'), nullable=False))
        if 'submitted_by' not in existing_cols:
            op.add_column('column_alias_cache', sa.Column('submitted_by', sa.BigInteger(), nullable=True))
        if 'approved_by' not in existing_cols:
            op.add_column('column_alias_cache', sa.Column('approved_by', sa.BigInteger(), nullable=True))

    if 'user_column_mappings' not in existing_tables:
        op.create_table(
            'user_column_mappings',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('headers_hash', sa.CHAR(length=64), nullable=False),
            sa.Column('header_row_index', sa.Integer(), server_default=sa.text('0'), nullable=False),
            sa.Column('mapping_json', sa.JSON(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            mysql_charset='utf8mb4',
            mysql_engine='InnoDB'
        )
        op.create_index('idx_user_col_map_user_hash', 'user_column_mappings', ['user_id', 'headers_hash'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'user_column_mappings' in existing_tables:
        op.drop_index('idx_user_col_map_user_hash', table_name='user_column_mappings')
        op.drop_table('user_column_mappings')

