import enum
from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, Boolean, DateTime,
    Numeric, Enum, JSON, ForeignKey, Index, CHAR, func
)
from sqlalchemy.orm import relationship
from database import Base

class RoleEnum(str, enum.Enum):
    admin = "admin"
    user = "user"

class AuthProviderEnum(str, enum.Enum):
    password = "password"
    google = "google"

class UserStatusEnum(str, enum.Enum):
    pending_verification = "pending_verification"
    pending_approval = "pending_approval"
    active = "active"
    disabled = "disabled"

class AnalysisStatusEnum(str, enum.Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, index=True, nullable=True)
    name = Column(String(120), nullable=False)
    first_name = Column(String(80), nullable=True)
    surname = Column(String(80), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    email_canonical = Column(String(255), unique=True, index=True, nullable=False)
    pending_email = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(Enum("admin", "user", name="user_role_enum"), default="user", nullable=False)
    auth_provider = Column(Enum("password", "google", name="auth_provider_enum"), default="password", nullable=False)
    google_sub = Column(String(64), unique=True, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    status = Column(Enum("pending_verification", "pending_approval", "active", "disabled", name="user_status_enum"), default="pending_verification", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    consented_at = Column(DateTime, nullable=True)
    terms_version = Column(String(20), nullable=True)
    daily_analyses_limit = Column(Integer, nullable=True)
    monthly_gemini_limit = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")
    verification_codes = relationship("EmailVerificationCode", back_populates="user", cascade="all, delete-orphan")
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_token_hash", "token_hash"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False)
    remember_me = Column(Boolean, default=False, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_active_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")

class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"
    __table_args__ = (
        Index("ix_email_verification_codes_user_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="verification_codes")

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_password_reset_tokens_user_id", "user_id"),
        Index("ix_password_reset_tokens_token_hash", "token_hash"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="reset_tokens")

class LoginEvent(Base):
    __tablename__ = "login_events"
    __table_args__ = (
        Index("idx_login_events_user_created", "user_id", "created_at"),
        Index("idx_login_events_email_created", "email_attempted", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    email_attempted = Column(String(255), nullable=False)
    success = Column(Boolean, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        Index("idx_analyses_user_created", "user_id", "created_at"),
        Index("idx_analyses_user_sha256", "user_id", "file_sha256"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)
    original_filename = Column(String(255), nullable=False)
    file_sha256 = Column(CHAR(64), nullable=False)
    master_version = Column(String(64), nullable=False)
    columns_order = Column(JSON, nullable=True)
    status = Column(Enum("processing", "completed", "failed", name="analysis_status_enum"), default="processing", nullable=False)
    rows_total = Column(Integer, default=0, nullable=False)
    rows_calculated = Column(Integer, default=0, nullable=False)
    rows_manual_review = Column(Integer, default=0, nullable=False)
    rows_not_applicable = Column(Integer, default=0, nullable=False)
    total_acquisition = Column(Numeric(20, 2), default=0.00, nullable=False)
    total_replacement = Column(Numeric(20, 2), default=0.00, nullable=False)
    gemini_calls = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="analyses")
    rows = relationship("AnalysisRow", back_populates="analysis", cascade="all, delete-orphan")

class AnalysisRow(Base):
    __tablename__ = "analysis_rows"
    __table_args__ = (
        Index("idx_analysis_rows_analysis_id", "analysis_id"),
        Index("idx_analysis_rows_analysis_status", "analysis_id", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    analysis_id = Column(BigInteger, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    row_no = Column(Integer, nullable=False)
    asset_code = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    capitalized_date = Column(String(100), nullable=True)
    purchase_year = Column(Integer, nullable=True)
    acquisition_value = Column(Numeric(20, 2), nullable=True)
    accumulated_dep = Column(Numeric(20, 2), nullable=True)
    book_value = Column(Numeric(20, 2), nullable=True)
    major_category = Column(String(255), nullable=True)
    sub_category = Column(String(255), nullable=True)
    asset_class = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    wpi_group = Column(String(255), nullable=True)
    wpi_series = Column(String(255), nullable=True)
    purchase_wpi = Column(Numeric(12, 6), nullable=True)
    current_wpi = Column(Numeric(12, 6), nullable=True)
    calculation_method = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    replacement_value = Column(Numeric(20, 2), nullable=True)
    difference = Column(Numeric(20, 2), nullable=True)
    increase_pct = Column(Numeric(12, 6), nullable=True)
    original_row = Column(JSON, nullable=True)

    analysis = relationship("Analysis", back_populates="rows")

class ClassificationCache(Base):
    __tablename__ = "classification_cache"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    description_hash = Column(CHAR(64), unique=True, index=True, nullable=False)
    normalized_description = Column(Text, nullable=False)
    wpi_group = Column(String(255), nullable=False)
    source = Column(String(50), nullable=False) # synonym, keyword, gemini, manual
    confirmed_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class ColumnAliasCache(Base):
    __tablename__ = "column_alias_cache"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    header_hash = Column(CHAR(64), unique=True, index=True, nullable=False)
    normalized_header = Column(String(255), nullable=False)
    original_header = Column(String(255), nullable=True)
    canonical_field = Column(String(100), nullable=False)
    status = Column(String(30), default="approved", nullable=False)  # approved, pending, rejected
    validation_summary = Column(String(255), nullable=True)
    sample_values = Column(JSON, nullable=True)
    validation_passed = Column(Boolean, default=True, nullable=False)
    submitted_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class UserColumnMapping(Base):
    __tablename__ = "user_column_mappings"
    __table_args__ = (
        Index("idx_user_col_map_user_hash", "user_id", "headers_hash"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    headers_hash = Column(CHAR(64), nullable=False)
    header_row_index = Column(Integer, default=0, nullable=False)
    mapping_json = Column(JSON, nullable=False)
    sample_headers = Column(JSON, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class AuditLogs(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_user_created", "user_id", "created_at"),
        Index("idx_audit_logs_email_created", "user_email", "created_at"),
        Index("idx_audit_logs_activity_created", "activity_type", "created_at"),
        Index("idx_audit_logs_status_created", "status", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String(255), nullable=True)
    activity_type = Column(String(100), nullable=False)
    file_name = Column(String(255), nullable=True)
    status = Column(String(30), default="SUCCESS", nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class CompanyIndustryCache(Base):
    __tablename__ = "company_industry_cache"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_hash = Column(CHAR(64), unique=True, index=True, nullable=False)
    normalized_name = Column(String(255), nullable=False)
    suggested_industries = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

