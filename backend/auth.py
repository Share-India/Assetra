import os
import re
import hashlib
import hmac
import secrets
import datetime
from datetime import timedelta, timezone
import threading
from typing import Optional, List, Tuple
import urllib.request
import urllib.parse
import json
import logging

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models

logger = logging.getLogger("auth")

# Security settings from environment
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-jwt-key-far-calculator-app-random-string-at-least-40-chars")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
RATE_LIMIT_FAILED_ATTEMPTS = 5
RATE_LIMIT_LOCKOUT_MINUTES = 15

# Sign-up rate limiting (10 per hour per IP)
SIGNUP_LIMIT_PER_HOUR = 10
SIGNUP_WINDOW_SECONDS = 3600
_signup_attempts: dict = {}
_signup_lock = threading.Lock()

# Common weak passwords list for strength enforcement (including 6-character common passwords)
COMMON_PASSWORDS = {
    "123456", "111111", "000000", "654321", "password", "qwerty", "123123",
    "admin1", "welcome", "secret", "abc123", "pass123", "login1", "master",
    "password123", "password1234", "12345678", "123456789", "1234567890",
    "qwerty12345", "welcome1234", "admin123456", "administrator", "letmein1234",
    "changeme123", "iloveyou123", "sunshine123", "master12345", "company1234",
    "password@123", "password!123", "admin@12345", "welcome@123", "secret12345"
}

from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

def get_remember_me_days() -> int:
    """Read REMEMBER_ME_DAYS from environment/.env, defaulting to 7."""
    load_dotenv(ENV_PATH, override=True)
    try:
        val = int(os.getenv("REMEMBER_ME_DAYS", "7").strip())
        return val if val > 0 else 7
    except Exception:
        return 7

def canonicalize_email(email: str) -> str:
    """
    Normalize and canonicalize an email address:
    - Trim whitespace and convert to lowercase.
    - For gmail.com and googlemail.com:
      - Remove all dots from the local part.
      - Remove anything after '+' in the local part.
      - Normalize domain to gmail.com.
    - For all other domains:
      - Lowercase only.
    """
    if not email:
        return ""
    clean = email.strip().lower()
    if "@" not in clean:
        return clean
    local_part, domain = clean.rsplit("@", 1)
    if domain in ("gmail.com", "googlemail.com"):
        local_part = local_part.split("+")[0].replace(".", "")
        domain = "gmail.com"
    return f"{local_part}@{domain}"

def get_idle_timeout_minutes() -> float:
    """Read IDLE_TIMEOUT_MINUTES from environment/.env, defaulting to 30."""
    load_dotenv(ENV_PATH, override=True)
    try:
        val = float(os.getenv("IDLE_TIMEOUT_MINUTES", "30").strip())
        return val if val > 0 else 30.0
    except Exception:
        return 30.0

def get_password_min_length() -> int:
    """Read PASSWORD_MIN_LENGTH from environment, defaulting to 6."""
    try:
        return int(os.getenv("PASSWORD_MIN_LENGTH", "6").strip())
    except Exception:
        return 6

def get_allowed_email_domains() -> List[str]:
    """Parse ALLOWED_EMAIL_DOMAINS from environment."""
    raw = os.getenv("ALLOWED_EMAIL_DOMAINS", "").strip()
    if not raw or raw == "*" or raw.lower() == "all":
        return []
    domains = [d.strip().lower() for d in raw.split(",") if d.strip()]
    if "*" in domains or "all" in domains:
        return []
    return domains

def is_domain_allowed(email: str) -> bool:
    """
    Check if the email domain matches ALLOWED_EMAIL_DOMAINS.
    Domain restriction is disabled by default; set ENFORCE_DOMAIN_RESTRICTION=true to enforce.
    """
    enforce = os.getenv("ENFORCE_DOMAIN_RESTRICTION", "false").strip().lower()
    if enforce not in ("true", "1", "yes"):
        # Domain restriction is not enabled; allow any valid email
        return True

    domains = get_allowed_email_domains()
    if not domains:
        return True
    if "@" not in email:
        return False
    domain = email.split("@")[-1].strip().lower()
    return domain in domains

def validate_password_strength(password: str, email: str = "") -> Tuple[bool, str]:
    """
    Enforce password rules:
    - At least PASSWORD_MIN_LENGTH (default 6) characters
    - At most 128 characters
    - Not the email or email username
    - Not in a common passwords list
    """
    min_length = get_password_min_length()
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    
    if email:
        email_clean = email.strip().lower()
        if password.lower() == email_clean:
            return False, "Password cannot be your email address."
        local_part = email_clean.split("@")[0]
        if local_part and len(local_part) >= 3 and password.lower() == local_part:
            return False, "Password cannot match your email username."
            
    if password.lower() in COMMON_PASSWORDS:
        return False, "Password is too common. Please choose a stronger password."
        
    return True, ""

def check_and_record_signup_rate_limit(ip_address: str) -> bool:
    """
    Rate limit sign-ups to 10 per hour per IP.
    Returns True if allowed (recording attempt), False if exceeded.
    """
    now = datetime.datetime.now(timezone.utc).timestamp()
    cutoff = now - SIGNUP_WINDOW_SECONDS
    with _signup_lock:
        timestamps = _signup_attempts.get(ip_address, [])
        timestamps = [ts for ts in timestamps if ts > cutoff]
        if len(timestamps) >= SIGNUP_LIMIT_PER_HOUR:
            _signup_attempts[ip_address] = timestamps
            return False
        timestamps.append(now)
        _signup_attempts[ip_address] = timestamps
        return True

def verify_turnstile(token: Optional[str], ip_address: Optional[str] = None) -> bool:
    """
    Validates Cloudflare Turnstile token if TURNSTILE_SECRET is configured.
    If secret is not set, defaults to True (pass-through for dev/testing).
    """
    secret = os.getenv("TURNSTILE_SECRET", "").strip()
    if not secret:
        return True
    if not token:
        return False
    try:
        url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        payload = {"secret": secret, "response": token}
        if ip_address:
            payload["remoteip"] = ip_address
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=5) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return bool(res_data.get("success", False))
    except Exception as e:
        logger.warning("Turnstile verification error: %s", str(e))
        return False

def verify_google_token(credential: str) -> Optional[dict]:
    """
    Securely verify a Google OAuth ID token against GOOGLE_CLIENT_ID.
    Returns dict with {'sub', 'email', 'email_verified', 'name', 'given_name', 'family_name'} or None.
    """
    load_dotenv(ENV_PATH, override=True)
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id or not credential:
        return None

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        idinfo = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            client_id
        )
        if idinfo.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            return None
        if not idinfo.get("email_verified"):
            return None
        return {
            "sub": str(idinfo.get("sub", "")),
            "email": str(idinfo.get("email", "")).strip().lower(),
            "email_verified": True,
            "name": str(idinfo.get("name") or idinfo.get("email", "").split("@")[0]),
            "given_name": str(idinfo.get("given_name") or ""),
            "family_name": str(idinfo.get("family_name") or ""),
        }
    except Exception:
        pass

    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(credential)}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode("utf-8"))
        if data.get("aud") != client_id:
            return None
        if data.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            return None
        if str(data.get("email_verified", "")).lower() != "true":
            return None
        return {
            "sub": str(data.get("sub", "")),
            "email": str(data.get("email", "")).strip().lower(),
            "email_verified": True,
            "name": str(data.get("name") or data.get("email", "").split("@")[0]),
            "given_name": str(data.get("given_name") or ""),
            "family_name": str(data.get("family_name") or ""),
        }
    except Exception as e:
        logger.warning("Google token verification error: %s", str(e))
        return None

def hash_code_or_token(raw_value: str) -> str:
    """Store only SHA-256 hashes of codes and tokens."""
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()

def verify_code_or_token(raw_value: str, expected_hash: str) -> bool:
    """Constant-time comparison of hashed codes or tokens."""
    computed_hash = hash_code_or_token(raw_value)
    return hmac.compare_digest(computed_hash, expected_hash)

def generate_verification_code() -> str:
    """Generate a 6-digit random numeric code."""
    return f"{secrets.randbelow(900000) + 100000}"

def generate_reset_token() -> str:
    """Generate a secure url-safe reset token."""
    return secrets.token_urlsafe(32)

security_bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hash password securely using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, password_hash: Optional[str] = None, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate signed JWT token.
    Attaches a signature snippet of password_hash so password resets invalidate previous sessions.
    """
    to_encode = data.copy()
    now = datetime.datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        
    pwd_salt = password_hash[-10:] if password_hash else ""
    to_encode.update({"exp": expire, "iat": now, "pwd_salt": pwd_salt})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session expired, please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def create_user_session(
    db: Session,
    user: models.User,
    remember_me: bool = False,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Tuple[str, models.UserSession]:
    """Create a JWT and persist a server-side session row in user_sessions."""
    now_utc = datetime.datetime.now(timezone.utc)
    if remember_me:
        expires_delta = timedelta(days=get_remember_me_days())
    else:
        expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    jti = secrets.token_hex(16)
    token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "jti": jti,
            "remember_me": bool(remember_me)
        },
        password_hash=user.password_hash,
        expires_delta=expires_delta
    )
    token_hash = hash_code_or_token(token)
    session_row = models.UserSession(
        user_id=user.id,
        token_hash=token_hash,
        remember_me=bool(remember_me),
        ip_address=ip_address,
        user_agent=(user_agent[:255] if user_agent else None),
        created_at=now_utc.replace(tzinfo=None),
        last_active_at=now_utc.replace(tzinfo=None),
        expires_at=(now_utc + expires_delta).replace(tzinfo=None),
        revoked_at=None
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)
    return token, session_row

def set_auth_cookie(response, token: str, remember_me: bool = False) -> None:
    """
    Set the access_token cookie on the response.
    - remember_me=False (unchecked): session cookie (no max_age / expires) that ends when the browser closes.
    - remember_me=True (checked): persistent cookie expiring after REMEMBER_ME_DAYS days.
    """
    is_prod = os.getenv("ENV", "development").strip().lower() == "production"
    if remember_me:
        days = get_remember_me_days()
        max_age = days * 86400
        expires = datetime.datetime.now(timezone.utc) + timedelta(days=days)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=is_prod,
            path="/",
            max_age=max_age,
            expires=expires
        )
    else:
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=is_prod,
            path="/"
        )

def revoke_user_session(db: Session, token: Optional[str]) -> bool:
    """Revoke the server-side session matching the given token."""
    if not token:
        return False
    token_hash = hash_code_or_token(token)
    now_naive = datetime.datetime.now(timezone.utc).replace(tzinfo=None)
    session_row = db.query(models.UserSession).filter(models.UserSession.token_hash == token_hash).first()
    if session_row:
        session_row.revoked_at = now_naive
        db.commit()
        return True
    return False

def get_failed_login_count(db: Session, email: str, ip_address: Optional[str]) -> int:
    """Count consecutive failed logins in the last 15 minutes (since the last successful login)."""
    email_clean = email.strip().lower()
    # Fetch recent login events for this email (newest first)
    recent_events = (
        db.query(models.LoginEvent)
        .filter(models.LoginEvent.email_attempted == email_clean)
        .order_by(models.LoginEvent.id.desc())
        .limit(RATE_LIMIT_FAILED_ATTEMPTS + 5)
        .all()
    )
    now_local = datetime.datetime.now()
    cutoff_local = now_local - timedelta(minutes=RATE_LIMIT_LOCKOUT_MINUTES)
    consecutive_failures = 0
    for ev in recent_events:
        if ev.success:
            # A successful login resets the consecutive failure streak
            break
        ev_time = ev.created_at.replace(tzinfo=None) if ev.created_at else now_local
        if ev_time < cutoff_local:
            break
        consecutive_failures += 1
    return consecutive_failures

def check_rate_limit(db: Session, email: str, ip_address: Optional[str]) -> bool:
    """
    Check if an email + IP is currently locked out due to >= 5 failed attempts in the last 15 minutes.
    Returns True if locked out, False if allowed.
    """
    return get_failed_login_count(db, email, ip_address) >= RATE_LIMIT_FAILED_ATTEMPTS

def record_login_event(
    db: Session,
    user_id: Optional[int],
    email: str,
    success: bool,
    ip_address: Optional[str],
    user_agent: Optional[str]
) -> models.LoginEvent:
    """Append-only audit record of every login attempt."""
    event = models.LoginEvent(
        user_id=user_id,
        email_attempted=email.strip().lower(),
        success=success,
        ip_address=ip_address,
        user_agent=(user_agent[:255] if user_agent else None)
    )
    db.add(event)
    db.commit()
    return event

def get_primary_admin_email() -> str:
    """
    Return the primary administrator email address.
    Defaults to communication.ins@shareindia.co.in unless overridden by ADMIN_EMAIL in .env.
    """
    load_dotenv(ENV_PATH, override=True)
    raw = os.getenv("ADMIN_EMAIL", "communication.ins@shareindia.co.in").strip()
    if not raw:
        raw = "communication.ins@shareindia.co.in"
    return raw.split(",")[0].strip().lower()


def is_primary_admin(user: Optional[models.User]) -> bool:
    """Check if the user is the permanent Primary Administrator."""
    if not user or not getattr(user, "email", None):
        return False
    return (user.email or "").strip().lower() == get_primary_admin_email()


def is_admin_user(user: Optional[models.User]) -> bool:
    """
    Check if the user has active administrative privileges.
    Applies equally to Primary Admin and any dynamically promoted Admin.
    """
    if not user:
        return False
    if getattr(user, "role", None) != "admin":
        return False
    if not bool(getattr(user, "email_verified", False)):
        return False
    if not bool(getattr(user, "is_active", False)):
        return False
    if getattr(user, "status", None) == "disabled":
        return False
    return True


def is_authorized_admin_user(user: Optional[models.User]) -> bool:
    """Verify that the user has verified administrative access (Primary or Promoted Admin)."""
    return is_admin_user(user)


def get_authorized_admin_emails() -> list:
    """Return list containing the primary admin email for backward compatibility."""
    return [get_primary_admin_email()]


def sync_user_admin_role(db: Session, user: Optional[models.User]) -> Optional[models.User]:
    """
    Ensure the user's role strictly reflects backend authorization:
    - Primary Admin always has role='admin', email_verified=True, status='active', is_active=True.
    - Dynamically promoted admins retain role='admin'.
    - Normal users remain role='user'.
    """
    if not user or not getattr(user, "email", None):
        return user
    email_clean = (user.email or "").strip().lower()
    primary_email = get_primary_admin_email()
    changed = False
    if email_clean == primary_email:
        if user.role != "admin":
            user.role = "admin"
            changed = True
        if not bool(user.email_verified):
            user.email_verified = True
            changed = True
        if user.status != "active":
            user.status = "active"
            changed = True
        if not bool(user.is_active):
            user.is_active = True
            changed = True

    if changed:
        try:
            db.commit()
            db.refresh(user)
        except Exception as e:
            logger.warning("Failed to commit sync_user_admin_role: %s", e)
            db.rollback()
    return user


def record_audit_event(
    db: Session,
    actor_id: Optional[int],
    action: str,
    target: Optional[str] = None,
    user_email: Optional[str] = None,
    file_name: Optional[str] = None,
    status: str = "SUCCESS",
    details: Optional[str] = None,
    ip_address: Optional[str] = None
) -> models.AuditLogs:
    """
    Record an explicit user/system activity in the persistent `audit_logs` table,
    while also maintaining `audit_log` for backward compatibility.
    Requirement 5: Audit details must use user IDs only; no emails stored in audit_logs.
    """
    from logger_config import redact_sensitive_text

    act_clean = (action or "SYSTEM_EVENT").strip().upper()
    raw_target = str(target).strip() if target else None
    raw_details = str(details).strip() if details else raw_target

    # Sanitize target to ensure it uses user ID only and never contains raw emails
    target_clean = None
    if raw_target:
        # replace user:id:email with user:id
        t = re.sub(r'user:(\d+):[^\s:]+', r'user:\1', raw_target)
        if 'email:' in t:
            t = f"user:{actor_id}" if actor_id else "user:unknown"
        t = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', f'user:{actor_id or "unknown"}', t)
        target_clean = redact_sensitive_text(t)

    # Sanitize details to ensure it uses user IDs only and never contains raw emails
    details_clean = None
    if raw_details:
        d = re.sub(r'user:(\d+):[^\s:]+', r'User ID #\1', raw_details)
        d = re.sub(r'email:[^\s:]+', f'User ID #{actor_id or "unknown"}', d)
        def _email_sub(m):
            return f"User ID #{actor_id}" if actor_id else "User ID #unknown"
        d = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', _email_sub, d)
        details_clean = redact_sensitive_text(d)

    resolved_file = file_name
    if not resolved_file and target_clean:
        if target_clean.startswith("file:"):
            resolved_file = target_clean.split("file:", 1)[1][:255]
        elif target_clean.startswith("analysis:"):
            parts = target_clean.split(":", 2)
            if len(parts) == 3:
                resolved_file = parts[2][:255]

    resolved_status = (status or "SUCCESS").strip().upper()
    if act_clean.endswith("_FAILED") or "REJECTED" in act_clean:
        resolved_status = "FAILED"

    # 1. Legacy audit_log row (kept intact with user IDs only)
    legacy_entry = models.AuditLog(
        actor_id=actor_id,
        action=act_clean[:100],
        target=(target_clean[:255] if target_clean else None)
    )
    db.add(legacy_entry)

    # 2. Primary persistent audit_logs row (user_email set to None per Requirement 5)
    audit_entry = models.AuditLogs(
        user_id=actor_id,
        user_email=None,
        activity_type=act_clean[:100],
        file_name=(resolved_file[:255] if resolved_file else None),
        status=resolved_status[:30],
        details=details_clean,
        ip_address=(ip_address[:45] if ip_address else None)
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry

def get_token_from_request(request: Request, creds: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> Optional[str]:
    """Retrieve token from Bearer header or httpOnly cookie."""
    if creds and creds.credentials:
        return creds.credentials
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        if cookie_token.startswith("Bearer "):
            return cookie_token[7:]
        return cookie_token
    return None

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db)
) -> models.User:
    """Authenticate current user from token. Rejects unverified, pending approval, or disabled users."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
        
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    user = sync_user_admin_role(db, user)
        
    # Check if session was invalidated by password change
    token_pwd_salt = payload.get("pwd_salt")
    if user.password_hash and token_pwd_salt is not None:
        current_pwd_salt = user.password_hash[-10:]
        if token_pwd_salt != current_pwd_salt:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalidated due to password change. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"}
            )

    # Check server-side session & idle timeout if session tracking is active for this token
    token_hash = hash_code_or_token(token)
    session_row = db.query(models.UserSession).filter(models.UserSession.token_hash == token_hash).first()
    if "jti" in payload or session_row is not None:
        if session_row is None or session_row.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session expired, please sign in again.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        now_naive = datetime.datetime.now(timezone.utc).replace(tzinfo=None)
        if session_row.expires_at and now_naive >= session_row.expires_at:
            session_row.revoked_at = now_naive
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session expired, please sign in again.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        idle_minutes = get_idle_timeout_minutes()
        if session_row.last_active_at and (now_naive - session_row.last_active_at) >= timedelta(minutes=idle_minutes):
            session_row.revoked_at = now_naive
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session expired, please sign in again.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        session_row.last_active_at = now_naive
        db.commit()

    user_status = getattr(user, "status", None)
    if user_status == "pending_verification":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email address to continue.")
    if user_status == "pending_approval":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account is awaiting admin approval.")
    if user_status == "disabled" or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled. Please contact administrator.")
        
    return user

def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Ensure authenticated user is an authorized administrator:
    - role == 'admin'
    - email_verified == True
    - is_active == True
    Grants equal administrative permissions to Primary Admin and any dynamically promoted Admin.
    """
    if not is_authorized_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Only authorized administrators may access this resource."
        )
    return current_user


def require_primary_admin(current_user: models.User = Depends(require_admin)) -> models.User:
    """
    Ensure authenticated user is the Primary Administrator.
    Only the Primary Admin can promote users to Admin or remove Admin privileges.
    """
    if not is_primary_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the Primary Admin can manage administrator roles."
        )
    return current_user

get_current_active_user = get_current_user
