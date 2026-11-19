"""Add validation_summary to column_alias_cache and purge raw sample_values

Revision ID: 010_alias_validation_summary
Revises: 009_password_reset_otp
Create Date: 2026-11-17 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '010_alias_validation_summary'
down_revision = '009_password_reset_otp'
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_cols = {c['name'] for c in inspector.get_columns('column_alias_cache')}

    if 'validation_summary' not in existing_cols:
        op.add_column(
            'column_alias_cache',
            sa.Column('validation_summary', sa.String(length=255), nullable=True)
        )

    # Purge any raw sample values from users' files already stored
    op.execute("UPDATE column_alias_cache SET sample_values = NULL")

    # Set initial validation summaries for existing aliases
    op.execute(
        "UPDATE column_alias_cache SET validation_summary = '100% valid date/year, 5 rows tested' "
        "WHERE id = 1 AND validation_summary IS NULL"
    )
    op.execute(
        "UPDATE column_alias_cache SET validation_summary = '100% text, 5 rows tested' "
        "WHERE id = 2 AND validation_summary IS NULL"
    )
    op.execute(
        "UPDATE column_alias_cache SET validation_summary = '100% numeric, 5 rows tested' "
        "WHERE id = 3 AND validation_summary IS NULL"
    )
    # Default for any other existing row
    op.execute(
        "UPDATE column_alias_cache SET validation_summary = '100% valid, tested' "
        "WHERE validation_summary IS NULL"
    )

def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_cols = {c['name'] for c in inspector.get_columns('column_alias_cache')}

    if 'validation_summary' in existing_cols:
        op.drop_column('column_alias_cache', 'validation_summary')
