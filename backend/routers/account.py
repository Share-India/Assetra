import re
import datetime
from datetime import timedelta, timezone
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
import models
import auth
import email_service

router = APIRouter(prefix="/account", tags=["account"])


def serialize_user_profile(user: models.User) -> dict:
    first_name = user.first_name
    surname = user.surname
    if not first_name and user.name:
        parts = user.name.strip().split()
        first_name = parts[0] if parts else ""
        if surname is None:
            surname = " ".join(parts[1:]) if len(parts) > 1 else ""
    username = user.username or (re.sub(r"[^a-z0-9_]", "", user.email.split("@")[0].lower()) + f"_{user.id}")
    return {
        "id": user.id,
        "username": username,
        "name": user.name,
        "first_name": first_name or "",
        "surname": surname or "",
        "email": user.email,
        "pending_email": user.pending_email,
        "role": user.role,
        "is_primary_admin": auth.is_primary_admin(user),
        "status": user.status,
        "email_verified": user.email_verified,
        "auth_provider": user.auth_provider,
        "has_password": bool(user.password_hash),
        "google_linked": bool(user.google_sub or user.auth_provider == "google"),
        "daily_analyses_limit": user.daily_analyses_limit,
        "monthly_gemini_limit": user.monthly_gemini_limit,
        "must_change_password": user.must_change_password,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


class UpdateProfileRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    surname: Optional[str] = Field("", max_length=80)
    email: Optional[str] = Field(None, max_length=255)


class VerifyEmailChangeRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=10)


class AccountChangePasswordRequest(BaseModel):
    current_password: Optional[str] = None
    new_password: str = Field(..., min_length=6, max_length=128)
    confirm_password: str = Field(..., min_length=6, max_length=128)


class DeleteAccountRequest(BaseModel):
    password: Optional[str] = None
    google_reauth_token: Optional[str] = None
    confirm_text: str = Field(..., description="Must be 'DELETE'")
    confirmed: bool = Field(..., description="Explicit confirmation checkbox")


@router.get("/profile")
def get_account_profile(
    current_user: models.User = Depends(auth.get_current_user),
):
    return {"user": serialize_user_profile(current_user)}


@router.put("/profile")
def update_account_profile(
    req: UpdateProfileRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    first_clean = req.first_name.strip()
    surname_clean = (req.surname or "").strip()
    if not first_clean:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="First name is required.")

    full_name = f"{first_clean} {surname_clean}".strip()
    current_user.first_name = first_clean
    current_user.surname = surname_clean
    current_user.name = full_name
    if not current_user.username:
        base_uname = re.sub(r"[^a-z0-9_]", "", current_user.email.split("@")[0].lower())
        current_user.username = f"{base_uname}_{current_user.id}"

    email_verification_sent = False
    if req.email is not None:
        new_email = req.email.strip().lower()
        if new_email and new_email != current_user.email.lower():
            if "@" not in new_email or "." not in new_email.split("@")[-1]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address format.")
            if not auth.is_domain_allowed(new_email):
                allowed_domains = ", ".join(auth.get_allowed_email_domains())
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email domain must be one of: {allowed_domains}"
                )
            existing = db.query(models.User).filter(
                models.User.email == new_email,
                models.User.id != current_user.id
            ).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That email address is already in use.")

            now_utc = datetime.datetime.now(timezone.utc)
            db.query(models.EmailVerificationCode).filter(
                models.EmailVerificationCode.user_id == current_user.id,
                models.EmailVerificationCode.used_at == None
            ).update({"used_at": now_utc})

            code = auth.generate_verification_code()
            code_record = models.EmailVerificationCode(
                user_id=current_user.id,
                code_hash=auth.hash_code_or_token(code),
                expires_at=now_utc + timedelta(minutes=15),
                attempts=0
            )
            db.add(code_record)
            current_user.pending_email = new_email
            db.commit()

            sent = email_service.send_verification_code_email(new_email, code)
            if not sent:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not send verification email to the new address. Please try again."
                )
            email_verification_sent = True

    db.commit()
    db.refresh(current_user)

    auth.record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="PROFILE_UPDATED",
        target=f"user:{current_user.id}:{current_user.email}",
        user_email=current_user.email,
        status="SUCCESS",
        details="User updated profile details" + (f" (pending email verification for {current_user.pending_email})" if email_verification_sent else "")
    )

    msg = "Profile details saved successfully."
    if email_verification_sent:
        msg = f"Profile saved. A 6-digit verification code has been sent to {current_user.pending_email} to confirm your email change."

    return {
        "message": msg,
        "email_verification_sent": email_verification_sent,
        "user": serialize_user_profile(current_user)
    }


@router.post("/verify-email-change")
def verify_email_change(
    req: VerifyEmailChangeRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.pending_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending email change to verify.")

    now_utc = datetime.datetime.now(timezone.utc)
    code_record = (
        db.query(models.EmailVerificationCode)
        .filter(
            models.EmailVerificationCode.user_id == current_user.id,
            models.EmailVerificationCode.used_at == None,
            models.EmailVerificationCode.expires_at > now_utc
        )
        .order_by(models.EmailVerificationCode.id.desc())
        .first()
    )

    if not code_record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code.")

    if code_record.attempts >= 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many failed attempts. Please initiate the email change again.")

    code_record.attempts += 1
    db.commit()

    if not auth.verify_code_or_token(req.code.strip(), code_record.code_hash):
        remaining = max(0, 5 - code_record.attempts)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid verification code. {remaining} attempt(s) remaining.")

    new_email = current_user.pending_email.strip().lower()
    existing = db.query(models.User).filter(
        models.User.email == new_email,
        models.User.id != current_user.id
    ).first()
    if existing:
        current_user.pending_email = None
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That email address is already taken.")

    code_record.used_at = now_utc
    current_user.email = new_email
    current_user.pending_email = None
    db.commit()
    db.refresh(current_user)

    auth.record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="PROFILE_UPDATED",
        target=f"user:{current_user.id}:email_changed",
        user_email=current_user.email,
        status="SUCCESS",
        details=f"Verified and updated email address to {current_user.email}"
    )

    return {
        "message": "Email address verified and updated successfully.",
        "user": serialize_user_profile(current_user)
    }


@router.post("/change-password")
def account_change_password(
    req: AccountChangePasswordRequest,
    request: Request,
    response: Response,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password and confirm password do not match.")

    # If user already has a password, require current_password verification
    if current_user.password_hash:
        if not req.current_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is required.")
        if not auth.verify_password(req.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
        if req.current_password == req.new_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password cannot be the same as your current password.")

    is_valid, err_msg = auth.validate_password_strength(req.new_password, email=current_user.email)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    current_user.password_hash = auth.hash_password(req.new_password)
    current_user.must_change_password = False
    db.commit()
    db.refresh(current_user)

    # Issue a fresh session token for the current session so the user stays signed in with the new password salt
    ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "")
    new_token, _ = auth.create_user_session(
        db=db,
        user=current_user,
        remember_me=False,
        ip_address=ip,
        user_agent=user_agent
    )
    auth.set_auth_cookie(response, new_token, remember_me=False)

    auth.record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="PASSWORD_CHANGED",
        target=f"user:{current_user.id}:{current_user.email}",
        user_email=current_user.email,
        status="SUCCESS",
        details="User updated account password",
        ip_address=ip
    )

    return {
        "message": "Password updated successfully.",
        "token": new_token,
        "user": serialize_user_profile(current_user)
    }


@router.get("/activity")
def get_account_activity(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    login_rows = (
        db.query(models.LoginEvent)
        .filter(models.LoginEvent.user_id == current_user.id)
        .order_by(desc(models.LoginEvent.created_at))
        .limit(20)
        .all()
    )
    analyses_rows = (
        db.query(models.Analysis)
        .filter(models.Analysis.user_id == current_user.id)
        .order_by(desc(models.Analysis.created_at))
        .limit(20)
        .all()
    )
    audit_rows = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.actor_id == current_user.id)
        .order_by(desc(models.AuditLog.created_at))
        .limit(30)
        .all()
    )

    return {
        "login_history": [
            {
                "id": e.id,
                "success": e.success,
                "ip_address": e.ip_address or "-",
                "user_agent": e.user_agent or "-",
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in login_rows
        ],
        "analysis_activities": [
            {
                "id": a.id,
                "original_filename": a.original_filename,
                "company_name": a.company_name or "",
                "status": a.status,
                "rows_total": a.rows_total or 0,
                "rows_calculated": a.rows_calculated or 0,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            }
            for a in analyses_rows
        ],
        "audit_events": [
            {
                "id": log.id,
                "action": log.action,
                "target": log.target,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in audit_rows
        ],
    }


@router.post("/delete")
def permanently_delete_account(
    req: DeleteAccountRequest,
    response: Response,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not req.confirmed or req.confirm_text.strip() != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please confirm account deletion by checking the box and typing DELETE."
        )

    # Protect the last admin account from accidental self-deletion
    if current_user.role == "admin":
        admin_count = db.query(models.User).filter(models.User.role == "admin", models.User.is_active == True).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only active administrator account."
            )

    # Verify identity via password re-authentication (or Google re-authentication for Google-only users)
    if current_user.password_hash:
        if not req.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please enter your password to confirm your identity."
            )
        if not auth.verify_password(req.password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password. Account deletion aborted."
            )
    else:
        # Google-only account without password
        if req.google_reauth_token:
            info = auth.verify_google_token(req.google_reauth_token)
            if not info or info.get("email", "").lower() != current_user.email.lower():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google re-authentication failed."
                )

    deleted_user_id = current_user.id

    # 1. Delete all sessions, verification codes, password reset tokens, and custom column mappings for this user
    db.query(models.UserSession).filter(models.UserSession.user_id == deleted_user_id).delete(synchronize_session=False)
    db.query(models.EmailVerificationCode).filter(models.EmailVerificationCode.user_id == deleted_user_id).delete(synchronize_session=False)
    db.query(models.PasswordResetToken).filter(models.PasswordResetToken.user_id == deleted_user_id).delete(synchronize_session=False)
    db.query(models.UserColumnMapping).filter(models.UserColumnMapping.user_id == deleted_user_id).delete(synchronize_session=False)

    # 2. Delete all analysis rows and analyses owned by this user only
    user_analysis_ids = [
        a_id for (a_id,) in db.query(models.Analysis.id).filter(models.Analysis.user_id == deleted_user_id).all()
    ]
    if user_analysis_ids:
        db.query(models.AnalysisRow).filter(models.AnalysisRow.analysis_id.in_(user_analysis_ids)).delete(synchronize_session=False)
        db.query(models.Analysis).filter(models.Analysis.id.in_(user_analysis_ids)).delete(synchronize_session=False)

    # 3. Anonymize login events and existing audit logs for this user (no PII left behind)
    db.query(models.LoginEvent).filter(models.LoginEvent.user_id == deleted_user_id).update(
        {"user_id": None, "email_attempted": f"deleted_user_{deleted_user_id}"},
        synchronize_session=False
    )
    db.query(models.AuditLog).filter(models.AuditLog.actor_id == deleted_user_id).update(
        {"actor_id": None, "target": f"deleted_user_id:{deleted_user_id}"},
        synchronize_session=False
    )
    db.query(models.AuditLogs).filter(models.AuditLogs.user_id == deleted_user_id).update(
        {
            "user_id": None,
            "user_email": f"deleted_user_{deleted_user_id}",
            "details": f"Anonymized activity for deleted_user_{deleted_user_id}"
        },
        synchronize_session=False
    )
    db.query(models.ClassificationCache).filter(models.ClassificationCache.confirmed_by == deleted_user_id).update(
        {"confirmed_by": None},
        synchronize_session=False
    )
    db.query(models.ColumnAliasCache).filter(models.ColumnAliasCache.submitted_by == deleted_user_id).update(
        {"submitted_by": None},
        synchronize_session=False
    )
    db.query(models.ColumnAliasCache).filter(models.ColumnAliasCache.approved_by == deleted_user_id).update(
        {"approved_by": None},
        synchronize_session=False
    )

    # 4. Delete the user record
    db.delete(current_user)
    db.commit()

    # 5. Record anonymized ACCOUNT_DELETED compliance audit log entry
    auth.record_audit_event(
        db=db,
        actor_id=None,
        action="ACCOUNT_DELETED",
        target=f"deleted_user_id:{deleted_user_id}",
        user_email=f"deleted_user_{deleted_user_id}",
        status="SUCCESS",
        details=f"Account and personal data permanently deleted (deleted_user_id={deleted_user_id})"
    )

    # 6. Clear authentication cookie
    response.delete_cookie(key="access_token", path="/", samesite="lax")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"

    return {
        "message": "Your account and associated personal data have been permanently deleted.",
        "deleted_user_id": deleted_user_id
    }

