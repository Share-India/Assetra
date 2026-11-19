"""Create initial tables for FAR Calculator

Revision ID: 001_initial_tables
Revises: 
Create Date: 2026-10-16 13:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '001_initial_tables'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'user', name='user_role_enum'), server_default='user', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('must_change_password', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB'
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. login_events
    op.create_table(
        'login_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('email_attempted', sa.String(length=255), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB'
    )
    op.create_index('idx_login_events_user_created', 'login_events', ['user_id', 'created_at'])
    op.create_index('idx_login_events_email_created', 'login_events', ['email_attempted', 'created_at'])

    # 3. analyses
    op.create_table(
        'analyses',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=255), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_sha256', sa.CHAR(length=64), nullable=False),
        sa.Column('master_version', sa.String(length=64), nullable=False),
        sa.Column('columns_order', sa.JSON(), nullable=True),
        sa.Column('status', sa.Enum('processing', 'completed', 'failed', name='analysis_status_enum'), server_default='processing', nullable=False),
        sa.Column('rows_total', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('rows_calculated', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('rows_manual_review', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('rows_not_applicable', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_acquisition', sa.Numeric(precision=20, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('total_replacement', sa.Numeric(precision=20, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('gemini_calls', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB'
    )
    op.create_index('idx_analyses_user_created', 'analyses', ['user_id', 'created_at'])
    op.create_index('idx_analyses_user_sha256', 'analyses', ['user_id', 'file_sha256'])

    # 4. analysis_rows
    op.create_table(
        'analysis_rows',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('analysis_id', sa.BigInteger(), nullable=False),
        sa.Column('row_no', sa.Integer(), nullable=False),
        sa.Column('asset_code', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('capitalized_date', sa.String(length=100), nullable=True),
        sa.Column('purchase_year', sa.Integer(), nullable=True),
        sa.Column('acquisition_value', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('accumulated_dep', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('book_value', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('major_category', sa.String(length=255), nullable=True),
        sa.Column('sub_category', sa.String(length=255), nullable=True),
        sa.Column('asset_class', sa.String(length=255), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('wpi_group', sa.String(length=255), nullable=True),
        sa.Column('wpi_series', sa.String(length=255), nullable=True),
        sa.Column('purchase_wpi', sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column('current_wpi', sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column('calculation_method', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('replacement_value', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('difference', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('increase_pct', sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column('original_row', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB'
    )
    op.create_index('idx_analysis_rows_analysis_id', 'analysis_rows', ['analysis_id'])
    op.create_index('idx_analysis_rows_analysis_status', 'analysis_rows', ['analysis_id', 'status'])

    # 5. classification_cache
    op.create_table(
        'classification_cache',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('description_hash', sa.CHAR(length=64), nullable=False),
        sa.Column('normalized_description', sa.Text(), nullable=False),
        sa.Column('wpi_group', sa.String(length=255), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('confirmed_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['confirmed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('description_hash'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB'
    )
    op.create_index(op.f('ix_classification_cache_description_hash'), 'classification_cache', ['description_hash'], unique=True)

    # 6. column_alias_cache
    op.create_table(
        'column_alias_cache',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('header_hash', sa.CHAR(length=64), nullable=False),
        sa.Column('normalized_header', sa.String(length=255), nullable=False),
        sa.Column('canonical_field', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('header_hash'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB'
    )
    op.create_index(op.f('ix_column_alias_cache_header_hash'), 'column_alias_cache', ['header_hash'], unique=True)

    # 7. audit_log
    op.create_table(
        'audit_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('actor_id', sa.BigInteger(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB'
    )

def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('column_alias_cache')
    op.drop_table('classification_cache')
    op.drop_table('analysis_rows')
    op.drop_table('analyses')
    op.drop_table('login_events')
    op.drop_table('users')
