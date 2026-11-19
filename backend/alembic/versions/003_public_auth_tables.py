"""Add public auth columns and tables for email verification, password reset, and google login

Revision ID: 003_public_auth_tables
Revises: 002_add_user_status
Create Date: 2026-10-19 14:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '003_public_auth_tables'
down_revision = '002_add_user_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update existing statuses so enum alter doesn't fail
    op.execute("UPDATE users SET status = 'active' WHERE status NOT IN ('active', 'disabled')")

    # 2. Alter status column enum on users
    op.alter_column(
        'users',
        'status',
        existing_type=sa.Enum('pending', 'active', 'rejected', 'disabled', name='user_status_enum'),
        type_=sa.Enum('pending_verification', 'pending_approval', 'active', 'disabled', name='user_status_enum'),
        server_default='pending_verification',
        nullable=False
    )

    # 3. Add new columns to users
    op.add_column(
        'users',
        sa.Column('auth_provider', sa.Enum('password', 'google', name='auth_provider_enum'), server_default='password', nullable=False)
    )
    op.add_column(
        'users',
        sa.Column('google_sub', sa.String(length=64), nullable=True)
    )
    op.create_unique_constraint('uq_users_google_sub', 'users', ['google_sub'])

    op.add_column(
        'users',
        sa.Column('email_verified', sa.Boolean(), server_default=sa.text('0'), nullable=False)
    )
    op.add_column(
        'users',
        sa.Column('consented_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('terms_version', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('daily_analyses_limit', sa.Integer(), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('monthly_gemini_limit', sa.Integer(), nullable=True)
    )

    # Allow nullable password_hash for Google auth users
    op.alter_column(
        'users',
        'password_hash',
        existing_type=sa.String(length=255),
        nullable=True
    )

    # Set email_verified=True for existing admins
    op.execute("UPDATE users SET email_verified = 1 WHERE role = 'admin'")

    # 4. Create email_verification_codes table
    op.create_table(
        'email_verification_codes',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB'
    )
    op.create_index(op.f('ix_email_verification_codes_user_id'), 'email_verification_codes', ['user_id'], unique=False)

    # 5. Create password_reset_tokens table
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB'
    )
    op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_password_reset_tokens_token_hash'), 'password_reset_tokens', ['token_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_password_reset_tokens_token_hash'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_user_id'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')

    op.drop_index(op.f('ix_email_verification_codes_user_id'), table_name='email_verification_codes')
    op.drop_table('email_verification_codes')

    op.alter_column('users', 'password_hash', existing_type=sa.String(length=255), nullable=False)
    op.drop_column('users', 'monthly_gemini_limit')
    op.drop_column('users', 'daily_analyses_limit')
    op.drop_column('users', 'terms_version')
    op.drop_column('users', 'consented_at')
    op.drop_column('users', 'email_verified')
    op.drop_constraint('uq_users_google_sub', 'users', type_='unique')
    op.drop_column('users', 'google_sub')
    op.drop_column('users', 'auth_provider')

    op.alter_column(
        'users',
        'status',
        existing_type=sa.Enum('pending_verification', 'pending_approval', 'active', 'disabled', name='user_status_enum'),
        type_=sa.Enum('pending', 'active', 'rejected', 'disabled', name='user_status_enum'),
        server_default='pending',
        nullable=False
    )
