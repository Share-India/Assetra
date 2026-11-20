import os
import re
import datetime
from datetime import timedelta, timezone
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from sqlalchemy.exc import IntegrityError

from database import get_db
import models
import auth
import email_service
from routers.account import serialize_user_profile

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1)
    remember_me: bool = False
    turnstile_token: Optional[str] = None

class GoogleLoginRequest(BaseModel):
    credential: str = Field(..., min_length=10)
    remember_me: bool = False

class SignUpRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1)
    confirm_password: Optional[str] = None
    consented: bool = Field(False, description="Consent to Terms of Use and Privacy Policy")
    turnstile_token: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

class VerifyEmailRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    code: str = Field(..., min_length=4, max_length=10)

class ResendCodeRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)

class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    turnstile_token: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    otp: Optional[str] = Field(None, description="6-digit verification code")
    token: Optional[str] = Field(None, description="OTP code or token")
    new_password: str = Field(..., min_length=1)
    confirm_password: Optional[str] = None

class VerifyResetOtpRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    otp: str = Field(..., min_length=6, max_length=6)

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)

@router.get("/config")
def get_auth_config():
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    email_verif = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").strip().lower() in ("true", "1", "yes")
    return {
        "google_configured": bool(google_client_id),
        "google_client_id": google_client_id,
        "email_verification_required": email_verif,
        "remember_me_days": auth.get_remember_me_days(),
        "idle_timeout_minutes": auth.get_idle_timeout_minutes()
    }

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

@router.post("/signup")
def signup(req: SignUpRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    email_clean = req.email.strip().lower()
    email_canonical = auth.canonicalize_email(email_clean)

    # 1. Rate limit sign-ups (10 per hour per IP)
    if not auth.check_and_record_signup_rate_limit(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-up attempts from this IP address. Please try again later."
        )

    # 2. Cloudflare Turnstile bot verification
    if not auth.verify_turnstile(req.turnstile_token, ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security bot check failed. Please refresh and try again."
        )

    # 3. Mandatory Terms & Privacy Policy Consent
    if not req.consented:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must agree to the Terms of Use and Privacy Policy to create an account."
        )

    # 4. Optional allowed email domain check (if configured in env)
    if not auth.is_domain_allowed(email_clean):
        allowed_domains = ", ".join(auth.get_allowed_email_domains())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration is restricted to authorized domains: {allowed_domains}"
        )

    # 5. Enforce password rules (6-128 chars, not email, not common password)
    is_valid, err_msg = auth.validate_password_strength(req.password, email=email_clean)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    # 6. Confirm password validation
    if req.confirm_password is not None and req.confirm_password != req.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match.")

    # 7. Check existing user against canonical and raw email
    existing_user = db.query(models.User).filter(
        or_(
            models.User.email_canonical == email_canonical,
            models.User.email == email_clean
        )
    ).first()

    if existing_user:
        # Case A: Account registered with Google
        if existing_user.auth_provider == "google" or existing_user.google_sub:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email is registered with Google. Please use Continue with Google."
            )

        # Case B: Verified account exists -> Create no row, send no code
        if existing_user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Sign in, or reset your password."
            )

        # Case C: Unverified account exists
        require_verif = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").strip().lower() in ("true", "1", "yes")
        if not require_verif:
            existing_user.name = req.name.strip()
            existing_user.password_hash = auth.hash_password(req.password)
            if not existing_user.email_canonical:
                existing_user.email_canonical = email_canonical
            existing_user.email_verified = True
            existing_user.is_active = True
            existing_user.status = "active"
            db.commit()
            db.refresh(existing_user)
            token_data = auth.create_access_token(
                data={"sub": str(existing_user.id), "email": existing_user.email, "role": existing_user.role}
            )
            return {
                "status": "active",
                "requires_verification": False,
                "token": token_data,
                "user": {
                    "id": existing_user.id,
                    "email": existing_user.email,
                    "name": existing_user.name,
                    "role": existing_user.role
                },
                "message": "Account created successfully."
            }

        now_utc = datetime.datetime.now(timezone.utc)
        recent_code = (
            db.query(models.EmailVerificationCode)
            .filter(models.EmailVerificationCode.user_id == existing_user.id)
            .order_by(desc(models.EmailVerificationCode.id))
            .first()
        )
        if recent_code and recent_code.created_at:
            code_created = recent_code.created_at.replace(tzinfo=timezone.utc) if recent_code.created_at.tzinfo is None else recent_code.created_at
            seconds_since = (now_utc - code_created).total_seconds()
            if seconds_since < 60:
                wait_seconds = max(1, int(60 - seconds_since))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"A verification code was recently sent. Please wait {wait_seconds} seconds before requesting another code."
                )

        # Invalidate earlier unused codes
        db.query(models.EmailVerificationCode).filter(
            models.EmailVerificationCode.user_id == existing_user.id,
            models.EmailVerificationCode.used_at == None
        ).update({"used_at": now_utc})

        # Update credentials on unverified account
        existing_user.name = req.name.strip()
        existing_user.password_hash = auth.hash_password(req.password)
        if not existing_user.email_canonical:
            existing_user.email_canonical = email_canonical

        code = auth.generate_verification_code()
        code_record = models.EmailVerificationCode(
            user_id=existing_user.id,
            code_hash=auth.hash_code_or_token(code),
            expires_at=now_utc + timedelta(minutes=15),
            attempts=0
        )
        db.add(code_record)
        db.commit()

        sent = email_service.send_verification_code_email(email_clean, code)
        if not sent:
            if not os.getenv("SMTP_HOST") or os.getenv("ENV", "development").strip().lower() == "development":
                return {
                    "status": "unverified_resend",
                    "dev_code": code,
                    "message": f"Verification code generated (SMTP not configured): {code}"
                }
            auth.record_audit_event(
                db=db,
                actor_id=existing_user.id,
                action="verification_email_failed",
                target=f"user:{existing_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="We couldn’t send the email, please try again"
            )

        return {
            "status": "unverified_resend",
            "message": "An unverified account with this email already exists. A new verification code has been sent to your email."
        }

    # 8. Create new user with unique canonical email
    require_verif = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").strip().lower() in ("true", "1", "yes")
    now_utc = datetime.datetime.now(timezone.utc)
    name_parts = req.name.strip().split()
    first_name = name_parts[0] if name_parts else req.name.strip()
    surname = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    new_user = models.User(
        name=req.name.strip(),
        first_name=first_name[:80],
        surname=surname[:80],
        email=email_clean,
        email_canonical=email_canonical,
        password_hash=auth.hash_password(req.password),
        role="user",
        auth_provider="password",
        status="active" if not require_verif else "pending_verification",
        email_verified=not require_verif,
        is_active=not require_verif,
        must_change_password=False,
        consented_at=now_utc,
        terms_version="1.0"
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        # Handle simultaneous sign-up race conditions gracefully
        concurrent_user = db.query(models.User).filter(
            or_(
                models.User.email_canonical == email_canonical,
                models.User.email == email_clean
            )
        ).first()
        if concurrent_user and (concurrent_user.auth_provider == "google" or concurrent_user.google_sub):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email is registered with Google. Please use Continue with Google."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Sign in, or reset your password."
            )

    if not new_user.username:
        base_uname = re.sub(r"[^a-z0-9_]", "", email_clean.split("@")[0].lower())
        new_user.username = f"{base_uname}_{new_user.id}"
        db.commit()
        db.refresh(new_user)

    # 9. If email verification is disabled, user is immediately active and authenticated!
    if not require_verif:
        auth.record_audit_event(
            db=db,
            actor_id=None,
            action="user_signup",
            target=f"user:{new_user.id}"
        )
        token_data = auth.create_access_token(
            data={"sub": str(new_user.id), "email": new_user.email, "role": new_user.role}
        )
        return {
            "status": "active",
            "requires_verification": False,
            "token": token_data,
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "name": new_user.name,
                "role": new_user.role
            },
            "message": "Account created successfully! Welcome to Assetra."
        }

    # 10. Email verification required: generate 6-digit code, store hash, send email
    code = auth.generate_verification_code()
    code_record = models.EmailVerificationCode(
        user_id=new_user.id,
        code_hash=auth.hash_code_or_token(code),
        expires_at=now_utc + timedelta(minutes=15),
        attempts=0
    )
    db.add(code_record)
    db.commit()

    sent = email_service.send_verification_code_email(email_clean, code)
    if not sent:
        if not os.getenv("SMTP_HOST") or os.getenv("ENV", "development").strip().lower() == "development":
            return {
                "status": "created",
                "dev_code": code,
                "message": f"Verification code generated (SMTP not configured): {code}"
            }
        auth.record_audit_event(
            db=db,
            actor_id=new_user.id,
            action="verification_email_failed",
            target=f"user:{new_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="We couldn’t send the email, please try again"
        )

    auth.record_audit_event(
        db=db,
        actor_id=None,
        action="user_signup",
        target=f"user:{new_user.id}"
    )

    return {
        "status": "created",
        "message": "A 6-digit verification code has been sent. Please check your inbox to activate your account."
    }

@router.post("/verify-email")
@router.post("/verify-code")
def verify_email(
    req: VerifyEmailRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    email_clean = req.email.strip().lower()
    email_canonical = auth.canonicalize_email(email_clean)
    user = db.query(models.User).filter(
        or_(
            models.User.email_canonical == email_canonical,
            models.User.email == email_clean
        )
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code."
        )

    now_utc = datetime.datetime.now(timezone.utc)

    # Find the most recent active code for this user
    code_record = (
        db.query(models.EmailVerificationCode)
        .filter(
            models.EmailVerificationCode.user_id == user.id,
            models.EmailVerificationCode.used_at == None,
            models.EmailVerificationCode.expires_at > now_utc
        )
        .order_by(models.EmailVerificationCode.id.desc())
        .first()
    )

    if not code_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code. Please request a new code."
        )

    # Check max attempts (at most 5 attempts allowed)
    if code_record.attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed attempts. This code is locked. Please request a new verification code."
        )

    # Increment attempts
    code_record.attempts += 1
    db.commit()

    # Constant-time comparison
    if not auth.verify_code_or_token(req.code.strip(), code_record.code_hash):
        remaining = max(0, 5 - code_record.attempts)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification code. {remaining} attempt(s) remaining."
        )

    # Code is valid! Mark as used
    code_record.used_at = now_utc
    user.email_verified = True

    # Check if admin approval is required
    require_approval = os.getenv("REQUIRE_ADMIN_APPROVAL", "false").strip().lower() == "true"
    if require_approval:
        user.status = "pending_approval"
        user.is_active = False
        db.commit()
        return {
            "message": "Email verified successfully. Your account is pending administrator approval before you can log in.",
            "status": "pending_approval",
            "email_verified": True
        }

    # Public active user
    user.status = "active"
    user.is_active = True
    user.last_login_at = now_utc
    db.commit()
    user = auth.sync_user_admin_role(db, user)

    # Issue JWT and create server-side session (default session cookie on initial verification)
    token, _ = auth.create_user_session(
        db=db,
        user=user,
        remember_me=False,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "")
    )
    auth.set_auth_cookie(response, token, remember_me=False)

    auth.record_audit_event(
        db=db,
        actor_id=user.id,
        action="email_verified",
        target=f"user:{user.id}"
    )

    return {
        "message": "Email verified successfully! You are now logged in.",
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "email_verified": user.email_verified
        }
    }

@router.post("/resend-code")
def resend_code(req: ResendCodeRequest, request: Request, db: Session = Depends(get_db)):
    email_clean = req.email.strip().lower()
    email_canonical = auth.canonicalize_email(email_clean)
    user = db.query(models.User).filter(
        or_(
            models.User.email_canonical == email_canonical,
            models.User.email == email_clean
        )
    ).first()

    # Generic response for anti-enumeration
    success_payload = {
        "message": "If this account is awaiting verification, a new 6-digit code has been sent."
    }

    if user:
        now_utc = datetime.datetime.now(timezone.utc)

        # 1. 60-second cooldown: check most recent code created
        last_code = (
            db.query(models.EmailVerificationCode)
            .filter(models.EmailVerificationCode.user_id == user.id)
            .order_by(models.EmailVerificationCode.created_at.desc())
            .first()
        )
        if last_code and last_code.created_at:
            created_tz = last_code.created_at.replace(tzinfo=timezone.utc) if last_code.created_at.tzinfo is None else last_code.created_at
            elapsed = (now_utc - created_tz).total_seconds()
            if elapsed < 60:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Please wait 60 seconds before requesting another code."
                )

        # 2. At most 5 per hour per user
        one_hour_ago = now_utc - timedelta(hours=1)
        hourly_count = (
            db.query(func.count(models.EmailVerificationCode.id))
            .filter(
                models.EmailVerificationCode.user_id == user.id,
                models.EmailVerificationCode.created_at >= one_hour_ago
            )
            .scalar() or 0
        )
        if hourly_count >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification requests. You can request at most 5 codes per hour."
            )

        # 3. Cancel older unused codes
        db.query(models.EmailVerificationCode).filter(
            models.EmailVerificationCode.user_id == user.id,
            models.EmailVerificationCode.used_at == None
        ).update({"used_at": now_utc})

        # 4. Generate new code
        code = auth.generate_verification_code()
        code_record = models.EmailVerificationCode(
            user_id=user.id,
            code_hash=auth.hash_code_or_token(code),
            expires_at=now_utc + timedelta(minutes=15),
            attempts=0
        )
        db.add(code_record)
        db.commit()

        # 5. Send email & check failure
        sent = email_service.send_verification_code_email(email_clean, code)
        if not sent:
            auth.record_audit_event(
                db=db,
                actor_id=user.id,
                action="verification_email_failed",
                target=f"user:{user.id}:{user.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="We couldn’t send the email, please try again"
            )

    return success_payload

@router.post("/login")
def login(login_req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    email = login_req.email.strip().lower()
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    # 1. Rate limit lockout check (5 failed attempts in 15 minutes)
    if auth.check_rate_limit(db, email, ip):
        auth.record_login_event(db, None, email, False, ip, user_agent)
        auth.record_audit_event(
            db=db,
            actor_id=None,
            action="LOGIN_FAILED",
            target=f"email:{email}",
            user_email=email,
            status="FAILED",
            details="Login blocked: account temporarily locked due to too many failed attempts",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to too many failed login attempts. Please try again in 15 minutes."
        )

    # 2. Turnstile check after 3 failed attempts
    failed_count = auth.get_failed_login_count(db, email, ip)
    if failed_count >= 3:
        if not auth.verify_turnstile(login_req.turnstile_token, ip):
            auth.record_audit_event(
                db=db,
                actor_id=None,
                action="LOGIN_FAILED",
                target=f"email:{email}",
                user_email=email,
                status="FAILED",
                details="Login blocked: security bot check failed after multiple attempts",
                ip_address=ip
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security bot check required after multiple attempts. Please complete the captcha."
            )

    # 3. Look up user by canonical or raw email
    email_canonical = auth.canonicalize_email(email)
    user = db.query(models.User).filter(
        or_(
            models.User.email_canonical == email_canonical,
            models.User.email == email
        )
    ).first()

    # 4. Verify password
    if not user or not user.password_hash or not auth.verify_password(login_req.password, user.password_hash):
        auth.record_login_event(db, user.id if user else None, email, False, ip, user_agent)
        auth.record_audit_event(
            db=db,
            actor_id=user.id if user else None,
            action="LOGIN_FAILED",
            target=f"email:{email}",
            user_email=email,
            status="FAILED",
            details="Invalid email or password",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # 5. Check user status
    if user.status == "pending_verification":
        auth.record_login_event(db, user.id, email, False, ip, user_agent)
        auth.record_audit_event(
            db=db,
            actor_id=user.id,
            action="LOGIN_FAILED",
            target=f"user:{user.id}:{email}",
            user_email=email,
            status="FAILED",
            details="Login blocked: email address not yet verified",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address to continue."
        )

    if user.status == "pending_approval":
        auth.record_login_event(db, user.id, email, False, ip, user_agent)
        auth.record_audit_event(
            db=db,
            actor_id=user.id,
            action="LOGIN_FAILED",
            target=f"user:{user.id}:{email}",
            user_email=email,
            status="FAILED",
            details="Login blocked: account awaiting admin approval",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is awaiting admin approval."
        )

    if user.status == "disabled" or not user.is_active:
        auth.record_login_event(db, user.id, email, False, ip, user_agent)
        auth.record_audit_event(
            db=db,
            actor_id=user.id,
            action="LOGIN_FAILED",
            target=f"user:{user.id}:{email}",
            user_email=email,
            status="FAILED",
            details="Login blocked: account is disabled",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Please contact administrator."
        )

    # 6. Success
    auth.record_login_event(db, user.id, email, True, ip, user_agent)
    auth.record_audit_event(
        db=db,
        actor_id=user.id,
        action="LOGIN_SUCCESS",
        target=f"user:{user.id}:{user.email}",
        user_email=user.email,
        status="SUCCESS",
        details="User signed in via email and password",
        ip_address=ip
    )
    user.last_login_at = func.now()
    db.commit()
    db.refresh(user)

    user = auth.sync_user_admin_role(db, user)

    remember_me = bool(login_req.remember_me)
    token, _ = auth.create_user_session(
        db=db,
        user=user,
        remember_me=remember_me,
        ip_address=ip,
        user_agent=user_agent
    )
    auth.set_auth_cookie(response, token, remember_me=remember_me)

    return {
        "token": token,
        "remember_me": remember_me,
        "remember_me_days": auth.get_remember_me_days(),
        "idle_timeout_minutes": auth.get_idle_timeout_minutes(),
        "user": serialize_user_profile(user)
    }

@router.post("/google")
def google_login(req: GoogleLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    info = auth.verify_google_token(req.credential)
    if not info or not info.get("email") or not info.get("sub"):
        auth.record_audit_event(
            db=db,
            actor_id=None,
            action="LOGIN_FAILED",
            target="google_oauth_invalid_token",
            status="FAILED",
            details="Google sign-in failed: invalid or expired Google token",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google authentication token."
        )

    email_clean = info["email"].strip().lower()
    google_sub = info["sub"]

    if not auth.is_domain_allowed(email_clean):
        allowed_domains = ", ".join(auth.get_allowed_email_domains())
        auth.record_audit_event(
            db=db,
            actor_id=None,
            action="LOGIN_FAILED",
            target=f"email:{email_clean}:google",
            user_email=email_clean,
            status="FAILED",
            details=f"Google sign-in blocked: unauthorized email domain ({email_clean})",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sign-in is restricted to authorized domains: {allowed_domains}"
        )

    # Avoid duplicate accounts: check by google_sub first, then by verified email
    user = db.query(models.User).filter(models.User.google_sub == google_sub).first()
    if not user:
        email_canonical = auth.canonicalize_email(email_clean)
        user = db.query(models.User).filter(
            or_(
                models.User.email_canonical == email_canonical,
                models.User.email == email_clean
            )
        ).first()

    now_utc = datetime.datetime.now(timezone.utc)
    if user:
        if user.status == "disabled" or (not user.is_active and user.status not in ("pending_verification",)):
            auth.record_login_event(db, user.id, email_clean, False, ip, user_agent)
            auth.record_audit_event(
                db=db,
                actor_id=user.id,
                action="LOGIN_FAILED",
                target=f"user:{user.id}:disabled",
                user_email=email_clean,
                status="FAILED",
                details="Google sign-in blocked: user account is disabled",
                ip_address=ip
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled. Please contact administrator."
            )
        if not user.google_sub:
            user.google_sub = google_sub
        if not getattr(user, "email_canonical", None):
            user.email_canonical = auth.canonicalize_email(user.email)
        user.email_verified = True
        if user.status == "pending_verification":
            user.status = "active"
            user.is_active = True
        user.last_login_at = func.now()
        db.commit()
        db.refresh(user)
    else:
        full_name = info.get("name") or email_clean.split("@")[0]
        first_name = info.get("given_name") or full_name.split()[0]
        surname = info.get("family_name") or (" ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else "")
        user = models.User(
            name=full_name[:120],
            first_name=first_name[:80],
            surname=surname[:80],
            email=email_clean,
            email_canonical=auth.canonicalize_email(email_clean),
            password_hash=None,
            role="user",
            auth_provider="google",
            google_sub=google_sub,
            email_verified=True,
            status="active",
            is_active=True,
            must_change_password=False,
            consented_at=now_utc,
            terms_version="1.0",
            last_login_at=func.now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        base_uname = re.sub(r"[^a-z0-9_]", "", email_clean.split("@")[0].lower())
        user.username = f"{base_uname}_{user.id}"
        db.commit()
        db.refresh(user)

    auth.record_login_event(db, user.id, email_clean, True, ip, user_agent)
    auth.record_audit_event(
        db=db,
        actor_id=user.id,
        action="GOOGLE_LOGIN",
        target=f"user:{user.id}:{user.email}:google",
        user_email=user.email,
        status="SUCCESS",
        details="User signed in via Google OAuth",
        ip_address=ip
    )

    user = auth.sync_user_admin_role(db, user)

    remember_me = bool(req.remember_me)
    token, _ = auth.create_user_session(
        db=db,
        user=user,
        remember_me=remember_me,
        ip_address=ip,
        user_agent=user_agent
    )
    auth.set_auth_cookie(response, token, remember_me=remember_me)

    return {
        "token": token,
        "remember_me": remember_me,
        "remember_me_days": auth.get_remember_me_days(),
        "idle_timeout_minutes": auth.get_idle_timeout_minutes(),
        "user": serialize_user_profile(user)
    }

@router.post("/admin-login")
def admin_login(login_req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    email = login_req.email.strip().lower()
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    # 1. Rate limit lockout check
    if auth.check_rate_limit(db, email, ip):
        auth.record_login_event(db, None, email, False, ip, user_agent)
        auth.record_audit_event(
            db=db,
            actor_id=None,
            action="LOGIN_FAILED",
            target=f"email:{email}:admin_portal",
            user_email=email,
            status="FAILED",
            details="Admin login blocked: account temporarily locked due to too many failed attempts",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to too many failed login attempts. Please try again in 15 minutes."
        )

    # 2. Turnstile check after 3 failed attempts
    failed_count = auth.get_failed_login_count(db, email, ip)
    if failed_count >= 3:
        if not auth.verify_turnstile(login_req.turnstile_token, ip):
            auth.record_audit_event(
                db=db,
                actor_id=None,
                action="LOGIN_FAILED",
                target=f"email:{email}:admin_portal",
                user_email=email,
                status="FAILED",
                details="Admin login blocked: security bot check failed",
                ip_address=ip
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security bot check required after multiple attempts. Please complete the captcha."
            )

    # 3. Look up user by canonical or raw email
    email_canonical = auth.canonicalize_email(email)
    user = db.query(models.User).filter(
        or_(
            models.User.email_canonical == email_canonical,
            models.User.email == email
        )
    ).first()

    # 4. Verify password
    if not user or not user.password_hash or not auth.verify_password(login_req.password, user.password_hash):
        auth.record_login_event(db, user.id if user else None, email, False, ip, user_agent)
        auth.record_audit_event(
            db=db,
            actor_id=user.id if user else None,
            action="LOGIN_FAILED",
            target=f"email:{email}:admin_portal",
            user_email=email,
            status="FAILED",
            details="Admin login failed: invalid email or password",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin email or password."
        )

    # 5. Role + Verified Email + Authorized Admin Email check
    if not auth.is_authorized_admin_user(user):
        auth.record_login_event(db, user.id, email, False, ip, user_agent)
        auth.record_audit_event(
            db=db,
            actor_id=user.id,
            action="LOGIN_FAILED",
            target=f"user:{user.id}:{user.email}",
            user_email=user.email,
            status="FAILED",
            details="Admin login rejected: account is not the authorized administrator",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This account does not have administrator privileges."
        )

    # 6. Check user status
    if user.status == "disabled" or not user.is_active:
        auth.record_login_event(db, user.id, email, False, ip, user_agent)
        auth.record_audit_event(
            db=db,
            actor_id=user.id,
            action="LOGIN_FAILED",
            target=f"user:{user.id}:{user.email}",
            user_email=user.email,
            status="FAILED",
            details="Admin login blocked: admin account is disabled",
            ip_address=ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is disabled. Please contact system administrator."
        )

    # 7. Success
    auth.record_login_event(db, user.id, email, True, ip, user_agent)
    auth.record_audit_event(
        db=db,
        actor_id=user.id,
        action="LOGIN_SUCCESS",
        target=f"user:{user.id}:{user.email}",
        user_email=user.email,
        status="SUCCESS",
        details="Administrator signed in via Admin Portal",
        ip_address=ip
    )
    user.last_login_at = func.now()
    db.commit()

    remember_me = bool(login_req.remember_me)
    token, _ = auth.create_user_session(
        db=db,
        user=user,
        remember_me=remember_me,
        ip_address=ip,
        user_agent=user_agent
    )
    auth.set_auth_cookie(response, token, remember_me=remember_me)

    return {
        "message": "Admin authenticated successfully",
        "token": token,
        "remember_me": remember_me,
        "remember_me_days": auth.get_remember_me_days(),
        "idle_timeout_minutes": auth.get_idle_timeout_minutes(),
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "email_verified": user.email_verified,
            "must_change_password": user.must_change_password
        }
    }

@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    email_clean = req.email.strip().lower()

    # Cloudflare Turnstile bot protection
    if not auth.verify_turnstile(req.turnstile_token, ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security bot check failed. Please refresh and try again."
        )

    # Anti-enumeration response: identical message regardless of account existence
    success_payload = {
        "message": "If that email is registered, a 6-digit verification OTP has been sent. Please check your inbox.",
        "status": "otp_sent",
        "email": email_clean
    }

    email_canonical = auth.canonicalize_email(email_clean)
    user = db.query(models.User).filter(
        or_(
            models.User.email_canonical == email_canonical,
            models.User.email == email_clean
        )
    ).first()

    if user and user.is_active and user.status == "active":
        now_utc = datetime.datetime.now(timezone.utc)
        # Invalidate prior unused tokens
        db.query(models.PasswordResetToken).filter(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.used_at == None
        ).update({"used_at": now_utc})

        # Generate 6-digit numeric OTP (NO link, NO token URL)
        otp = auth.generate_verification_code()
        token_hash = auth.hash_code_or_token(otp)
        reset_record = models.PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now_utc + timedelta(minutes=10),  # 10-minute expiry
            attempts=0,
            used_at=None
        )
        db.add(reset_record)
        db.commit()

        # Send password reset email containing ONLY the 6-digit OTP (no links or token URLs)
        email_service.send_password_reset_otp_email(user.email, otp)

        auth.record_audit_event(
            db=db,
            actor_id=user.id,
            action="PASSWORD_RESET_REQUESTED",
            target=f"user:{user.id}",
            status="SUCCESS",
            details="6-digit OTP generated and sent for password reset (10 min expiry)"
        )

        if email_service.is_test_mode():
            success_payload["dev_code"] = otp

    return success_payload

@router.post("/verify-reset-otp")
def verify_reset_otp(req: VerifyResetOtpRequest, db: Session = Depends(get_db)):
    """Pre-verify that the 6-digit OTP is valid and not expired before setting a new password."""
    email_clean = req.email.strip().lower()
    email_canonical = auth.canonicalize_email(email_clean)
    user = db.query(models.User).filter(
        or_(
            models.User.email_canonical == email_canonical,
            models.User.email == email_clean
        )
    ).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")

    now_utc = datetime.datetime.now(timezone.utc)
    token_record = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.used_at == None,
            models.PasswordResetToken.expires_at > now_utc
        )
        .order_by(models.PasswordResetToken.id.desc())
        .first()
    )
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The verification code has expired or is invalid. Please request a new 6-digit OTP."
        )

    if token_record.attempts >= 5:
        token_record.used_at = now_utc
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed attempts. This code has been invalidated. Please request a new code."
        )

    if not auth.verify_code_or_token(req.otp.strip(), token_record.token_hash):
        token_record.attempts += 1
        db.commit()
        remaining = max(0, 5 - token_record.attempts)
        if remaining == 0:
            token_record.used_at = now_utc
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many failed attempts. This code has been invalidated. Please request a new code."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid 6-digit OTP. {remaining} attempt(s) remaining."
        )

    return {"message": "OTP verified successfully.", "valid": True}

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    # 1. Password match check
    if req.confirm_password is not None and req.confirm_password != req.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match.")

    # 2. Password strength validation
    email_clean = (req.email or "").strip().lower()
    is_valid, err_msg = auth.validate_password_strength(req.new_password, email=email_clean)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    # 3. Locate user
    email_canonical = auth.canonicalize_email(email_clean)
    user = db.query(models.User).filter(
        or_(
            models.User.email_canonical == email_canonical,
            models.User.email == email_clean
        )
    ).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password reset request.")

    # 4. Extract OTP code (accepts req.otp or req.token)
    otp_code = (req.otp or req.token or "").strip()
    if not otp_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please enter the 6-digit verification OTP.")

    # 5. Look up active reset token for this user
    now_utc = datetime.datetime.now(timezone.utc)
    token_record = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.used_at == None,
            models.PasswordResetToken.expires_at > now_utc
        )
        .order_by(models.PasswordResetToken.id.desc())
        .first()
    )

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The verification OTP has expired or is invalid. Please request a new code."
        )

    # 6. Check attempt limit (max 5 attempts)
    if token_record.attempts >= 5:
        token_record.used_at = now_utc
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed attempts. This OTP has been invalidated. Please request a new code."
        )

    # 7. Constant-time OTP verification
    if not auth.verify_code_or_token(otp_code, token_record.token_hash):
        token_record.attempts += 1
        db.commit()
        remaining = max(0, 5 - token_record.attempts)
        if remaining == 0:
            token_record.used_at = now_utc
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many failed attempts. This code has been invalidated. Please request a new code."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid 6-digit OTP. {remaining} attempt(s) remaining."
        )

    # 8. Success: Update password and invalidate token & existing sessions
    user.password_hash = auth.hash_password(req.new_password)
    user.must_change_password = False
    token_record.used_at = now_utc

    # Invalidate all existing sessions
    db.query(models.UserSession).filter(
        models.UserSession.user_id == user.id,
        models.UserSession.revoked_at == None
    ).update({"revoked_at": now_utc.replace(tzinfo=None)})
    db.commit()

    auth.record_audit_event(
        db=db,
        actor_id=user.id,
        action="PASSWORD_CHANGED",
        target=f"user:{user.id}:{user.email}:reset",
        user_email=user.email,
        status="SUCCESS",
        details="User successfully reset password using 6-digit OTP verification code"
    )

    return {"message": "Password has been reset successfully. You can now log in with your new password."}

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    token: Optional[str] = Depends(auth.get_token_from_request),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    actor_id = None
    actor_email = None
    if token:
        try:
            payload = auth.decode_access_token(token)
            if payload.get("sub"):
                actor_id = int(payload["sub"])
            actor_email = payload.get("email")
        except Exception:
            pass
    revoked = auth.revoke_user_session(db, token)
    if actor_id:
        auth.record_audit_event(
            db=db,
            actor_id=actor_id,
            action="LOGOUT",
            target=f"user:{actor_id}",
            user_email=actor_email,
            status="SUCCESS",
            details="User signed out",
            ip_address=ip
        )
    response.delete_cookie(key="access_token", path="/", samesite="lax")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return {"message": "Logged out successfully", "session_revoked": revoked}

@router.get("/me")
def get_me(
    response: Response,
    token: Optional[str] = Depends(auth.get_token_from_request),
    current_user: models.User = Depends(auth.get_current_user)
):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    profile = serialize_user_profile(current_user)
    profile["token"] = token
    profile["idle_timeout_minutes"] = auth.get_idle_timeout_minutes()
    profile["remember_me_days"] = auth.get_remember_me_days()
    return profile

@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    if not current_user.password_hash or not auth.verify_password(req.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    is_valid, err_msg = auth.validate_password_strength(req.new_password, email=current_user.email)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    current_user.password_hash = auth.hash_password(req.new_password)
    current_user.must_change_password = False
    db.commit()

    auth.record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="PASSWORD_CHANGED",
        target=f"user:{current_user.id}:{current_user.email}",
        user_email=current_user.email,
        status="SUCCESS",
        details="User changed password",
        ip_address=ip
    )

    return {"message": "Password changed successfully."}
