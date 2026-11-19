"""Create audit_logs table and migrate existing audit_log and login_events records safely

Revision ID: 007_create_audit_logs_table
Revises: 006_column_mapping_upgrade
Create Date: 2026-11-16 04:18:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = '007_create_audit_logs_table'
down_revision = '006_column_mapping_upgrade'
branch_labels = None
depends_on = None


def _parse_legacy_audit_row(action: str, target: str, email_from_join: str):
    act_upper = (action or "").strip().upper()
    target_str = (target or "").strip()
    file_name = None
    status = "SUCCESS"
    activity_type = act_upper or "SYSTEM_EVENT"

    if act_upper == "LOGIN_SUCCESS":
        if target_str.endswith(":google"):
            activity_type = "GOOGLE_LOGIN"
        else:
            activity_type = "LOGIN_SUCCESS"
    elif act_upper in ("ADMIN_LOGGED_IN",):
        activity_type = "LOGIN_SUCCESS"
    elif act_upper in ("ADMIN_LOGIN_REJECTED_NOT_ADMIN", "LOGIN_FAILED"):
        activity_type = "LOGIN_FAILED"
        status = "FAILED"
    elif act_upper == "FILE_UPLOAD":
        activity_type = "FILE_UPLOAD"
        if target_str.startswith("file:"):
            file_name = target_str.split("file:", 1)[1]
    elif act_upper == "ANALYSIS_STARTED":
        activity_type = "ANALYSIS_STARTED"
        parts = target_str.split(":", 2)
        if len(parts) == 3:
            file_name = parts[2]
    elif act_upper == "ANALYSIS_COMPLETED":
        activity_type = "ANALYSIS_COMPLETED"
        parts = target_str.split(":", 2)
        if len(parts) == 3:
            file_name = parts[2]
    elif act_upper == "ANALYSIS_FAILED":
        activity_type = "ANALYSIS_FAILED"
        status = "FAILED"
        parts = target_str.split(":", 2)
        if len(parts) == 3:
            file_name = parts[2]
    elif act_upper in ("ACCOUNT_UPDATED", "PROFILE_UPDATED"):
        activity_type = "PROFILE_UPDATED"
    elif act_upper in ("PASSWORD_CHANGED", "PASSWORD_RESET", "PASSWORD_RESET_REQUESTED"):
        activity_type = "PASSWORD_CHANGED" if act_upper != "PASSWORD_RESET_REQUESTED" else "PASSWORD_RESET_REQUESTED"
    elif act_upper == "ACCOUNT_DELETED":
        activity_type = "ACCOUNT_DELETED"
    elif act_upper == "LOGOUT":
        activity_type = "LOGOUT"

    user_email = email_from_join
    if not user_email and target_str.startswith("user:"):
        parts = target_str.split(":")
        if len(parts) >= 3 and "@" in parts[2]:
            user_email = parts[2]

    return activity_type, file_name, status, user_email, target_str


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'audit_logs' not in existing_tables:
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=True),
            sa.Column('user_email', sa.String(length=255), nullable=True),
            sa.Column('activity_type', sa.String(length=100), nullable=False),
            sa.Column('file_name', sa.String(length=255), nullable=True),
            sa.Column('status', sa.String(length=30), server_default='SUCCESS', nullable=False),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            mysql_charset='utf8mb4',
            mysql_engine='InnoDB'
        )
        op.create_index('idx_audit_logs_user_created', 'audit_logs', ['user_id', 'created_at'], unique=False)
        op.create_index('idx_audit_logs_email_created', 'audit_logs', ['user_email', 'created_at'], unique=False)
        op.create_index('idx_audit_logs_activity_created', 'audit_logs', ['activity_type', 'created_at'], unique=False)
        op.create_index('idx_audit_logs_status_created', 'audit_logs', ['status', 'created_at'], unique=False)

    # Safely migrate existing rows from audit_log and failed login_events if audit_logs is currently empty
    existing_count = bind.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar() or 0
    if existing_count == 0:
        if 'audit_log' in existing_tables:
            rows = bind.execute(
                text(
                    "SELECT a.id, a.actor_id, a.action, a.target, a.created_at, u.email "
                    "FROM audit_log a LEFT JOIN users u ON a.actor_id = u.id ORDER BY a.id ASC"
                )
            ).fetchall()
            for r in rows:
                act_type, fname, st, u_email, details = _parse_legacy_audit_row(r[2], r[3], r[5])
                bind.execute(
                    text(
                        "INSERT INTO audit_logs (user_id, user_email, activity_type, file_name, status, details, created_at) "
                        "VALUES (:uid, :uemail, :atype, :fname, :st, :details, :cat)"
                    ),
                    {
                        "uid": r[1],
                        "uemail": u_email,
                        "atype": act_type,
                        "fname": fname,
                        "st": st,
                        "details": details,
                        "cat": r[4]
                    }
                )

        if 'login_events' in existing_tables:
            failed_logins = bind.execute(
                text(
                    "SELECT le.user_id, le.email_attempted, le.ip_address, le.created_at "
                    "FROM login_events le WHERE le.success = 0 ORDER BY le.id ASC"
                )
            ).fetchall()
            for fl in failed_logins:
                bind.execute(
                    text(
                        "INSERT INTO audit_logs (user_id, user_email, activity_type, file_name, status, details, ip_address, created_at) "
                        "VALUES (:uid, :uemail, 'LOGIN_FAILED', NULL, 'FAILED', 'Failed login attempt (migrated from login_events)', :ip, :cat)"
                    ),
                    {
                        "uid": fl[0],
                        "uemail": fl[1],
                        "ip": fl[2],
                        "cat": fl[3]
                    }
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'audit_logs' in existing_tables:
        op.drop_index('idx_audit_logs_status_created', table_name='audit_logs')
        op.drop_index('idx_audit_logs_activity_created', table_name='audit_logs')
        op.drop_index('idx_audit_logs_email_created', table_name='audit_logs')
        op.drop_index('idx_audit_logs_user_created', table_name='audit_logs')
        op.drop_table('audit_logs')

