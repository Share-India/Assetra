import datetime
import math
import os
import re
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from database import get_db
import models
import auth

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(auth.require_admin)])

class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6)
    role: str = Field("user", pattern="^(admin|user)$")

class UpdateUserStatusRequest(BaseModel):
    is_active: bool

class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6)

class PromoteAdminRequest(BaseModel):
    email: EmailStr

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.id.asc()).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "status": u.status,
            "is_active": u.is_active,
            "must_change_password": u.must_change_password,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        }
        for u in users
    ]

@router.get("/pending-requests")
def list_pending_requests(db: Session = Depends(get_db)):
    pending_users = db.query(models.User).filter(models.User.status == "pending_approval").order_by(desc(models.User.created_at)).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in pending_users
    ]

@router.post("/users/{user_id}/approve")
def approve_user(
    user_id: int,
    current_admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.status = "active"
    user.is_active = True
    db.commit()
    db.refresh(user)
    auth.record_audit_event(
        db,
        actor_id=current_admin.id,
        action="USER_APPROVED",
        target=f"user:{user.id}",
        status="SUCCESS",
        details=f"Admin approved user #{user.id}"
    )

    return {
        "message": f"User #{user.id} approved successfully.",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "status": user.status,
            "is_active": user.is_active
        }
    }

@router.post("/users/{user_id}/reject")
def reject_user(
    user_id: int,
    current_admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.status = "disabled"
    user.is_active = False
    db.commit()
    db.refresh(user)
    auth.record_audit_event(
        db,
        actor_id=current_admin.id,
        action="USER_REJECTED",
        target=f"user:{user.id}",
        status="SUCCESS",
        details=f"Admin rejected user registration #{user.id}"
    )

    return {
        "message": f"User #{user.id} registration rejected.",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "status": user.status,
            "is_active": user.is_active
        }
    }

# ==========================================
# Dynamic Admin Role Management Endpoints
# ==========================================

@router.get("/admins")
def list_admins(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(auth.require_admin)
):
    """
    List all administrators. Accessible to all admins (Primary & Promoted).
    """
    admins = (
        db.query(models.User)
        .filter(models.User.role == "admin")
        .order_by(models.User.id.asc())
        .all()
    )
    primary_email = auth.get_primary_admin_email()
    return [
        {
            "id": a.id,
            "name": a.name,
            "email": a.email,
            "role": a.role,
            "is_primary_admin": ((a.email or "").strip().lower() == primary_email),
            "status": a.status,
            "is_active": a.is_active,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "last_login_at": a.last_login_at.isoformat() if a.last_login_at else None,
        }
        for a in admins
    ]

@router.post("/admins/promote")
def promote_user_to_admin(
    payload: PromoteAdminRequest,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(auth.require_admin)
):
    """
    Promote a registered user to Administrator.
    Accessible to all users with the Admin role (permission depends on admin role, not specific user).
    """
    email_clean = payload.email.strip().lower()
    user = db.query(models.User).filter(func.lower(models.User.email) == email_clean).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{payload.email}' is not registered in the system."
        )
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{user.email}' is already an Administrator."
        )

    user.role = "admin"
    user.status = "active"
    user.is_active = True
    user.email_verified = True
    db.commit()
    db.refresh(user)

    auth.record_audit_event(
        db=db,
        actor_id=current_admin.id,
        action="ADMIN_PROMOTED",
        target=f"user:{user.id}",
        status="SUCCESS",
        details=f"User ID #{user.id} ({user.email}) promoted to Administrator by Admin ID #{current_admin.id}"
    )

    primary_email = auth.get_primary_admin_email()
    return {
        "message": f"User {user.name} ({user.email}) has been successfully promoted to Administrator.",
        "admin": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_primary_admin": ((user.email or "").strip().lower() == primary_email),
            "status": user.status,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }
    }

@router.post("/admins/{user_id}/demote")
def demote_admin_to_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(auth.require_admin)
):
    """
    Remove Administrator privileges from an admin, returning them to normal user role.
    Permission depends on admin role.
    Never allows removing the last administrator in the system.
    """
    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    if target.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not currently an administrator."
        )

    # Check that at least one admin remains in the system
    total_admins = db.query(func.count(models.User.id)).filter(models.User.role == "admin").scalar() or 0
    if total_admins <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last administrator. The system must retain at least one administrator."
        )

    target.role = "user"
    # Invalidate existing active sessions for security so admin tokens expire immediately
    db.query(models.UserSession).filter(
        models.UserSession.user_id == target.id,
        models.UserSession.revoked_at.is_(None)
    ).update({models.UserSession.revoked_at: func.now()})

    db.commit()
    db.refresh(target)

    auth.record_audit_event(
        db=db,
        actor_id=current_admin.id,
        action="ADMIN_DEMOTED",
        target=f"user:{target.id}",
        status="SUCCESS",
        details=f"User ID #{target.id} ({target.email}) demoted to Normal User by Admin ID #{current_admin.id}"
    )

    return {
        "message": f"Administrator privileges removed for {target.name} ({target.email}). User role changed to Normal User."
    }

ACTION_PLAIN_WORDS = {
    "LOGIN_SUCCESS": "Signed in",
    "LOGIN_FAILED": "Sign-in failed",
    "GOOGLE_LOGIN": "Google sign-in",
    "LOGOUT": "Signed out",
    "FILE_UPLOAD": "Uploaded FAR file",
    "UPLOAD_FAILED": "Upload failed",
    "ANALYSIS_STARTED": "Analysis started",
    "ANALYSIS_COMPLETED": "Analysis completed",
    "ANALYSIS_FAILED": "Analysis failed",
    "PROFILE_UPDATED": "Profile updated",
    "PASSWORD_CHANGED": "Password changed",
    "ACCOUNT_DELETED": "Account deleted",
    "USER_CREATED": "User account created",
    "USER_APPROVED": "User account approved",
    "USER_REJECTED": "User account rejected",
    "USER_ENABLED": "User account enabled",
    "USER_DISABLED": "User account disabled",
    "PASSWORD_RESET_REQUESTED": "Password reset requested",
    "ADMIN_PROMOTED": "Promoted to Admin",
    "ADMIN_DEMOTED": "Demoted from Admin",
}

ACTION_CATEGORIES = {
    "sign-in": ["LOGIN_SUCCESS", "LOGIN_FAILED", "GOOGLE_LOGIN", "LOGOUT", "PASSWORD_RESET_REQUESTED"],
    "upload": ["FILE_UPLOAD", "UPLOAD_FAILED"],
    "analysis": ["ANALYSIS_STARTED", "ANALYSIS_COMPLETED", "ANALYSIS_FAILED"],
    "account": ["USER_CREATED", "USER_APPROVED", "USER_REJECTED", "USER_ENABLED", "USER_DISABLED", "PROFILE_UPDATED", "PASSWORD_CHANGED", "ACCOUNT_DELETED", "ADMIN_PROMOTED", "ADMIN_DEMOTED"]
}

@router.get("/audit-logs")
def list_audit_logs(
    search: Optional[str] = Query(None, description="Search by user name, file name, activity, or details"),
    user: Optional[str] = Query(None, description="Filter by user name or user_id"),
    action_type: Optional[str] = Query(None, description="Filter by action category (sign-in, upload, analysis, account) or specific activity"),
    activity: Optional[str] = Query(None, description="Legacy activity alias"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (SUCCESS or FAILED)"),
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=1000, description="Items per page"),
    limit: Optional[int] = Query(None, le=1000, description="Legacy limit override"),
    db: Session = Depends(get_db)
):
    search_str = search if isinstance(search, str) else None
    user_str = user if isinstance(user, str) else None
    act_str = action_type if isinstance(action_type, str) else (activity if isinstance(activity, str) else None)
    status_str = status_filter if isinstance(status_filter, str) else None
    date_from_str = date_from if isinstance(date_from, str) else None
    date_to_str = date_to if isinstance(date_to, str) else None
    page_int = page if isinstance(page, int) else 1
    page_size_int = page_size if isinstance(page_size, int) else 25
    limit_int = limit if isinstance(limit, int) else None

    q = (
        db.query(models.AuditLogs, models.User.name)
        .outerjoin(models.User, models.AuditLogs.user_id == models.User.id)
    )

    if search_str and search_str.strip():
        term = f"%{search_str.strip()}%"
        q = q.filter(
            or_(
                models.User.name.ilike(term),
                models.AuditLogs.activity_type.ilike(term),
                models.AuditLogs.file_name.ilike(term),
                models.AuditLogs.details.ilike(term),
                models.AuditLogs.ip_address.ilike(term),
            )
        )

    if user_str and user_str.strip():
        u_clean = user_str.strip()
        if u_clean.isdigit():
            q = q.filter(models.AuditLogs.user_id == int(u_clean))
        else:
            q = q.filter(models.User.name.ilike(f"%{u_clean}%"))

    # Action category or specific activity filter
    filter_act = (act_str or "").strip().lower()
    if filter_act and filter_act != "all":
        if filter_act in ACTION_CATEGORIES:
            allowed_acts = ACTION_CATEGORIES[filter_act]
            q = q.filter(models.AuditLogs.activity_type.in_(allowed_acts))
        else:
            q = q.filter(func.upper(models.AuditLogs.activity_type) == filter_act.upper())

    if status_str and status_str.strip() and status_str.strip().upper() != "ALL":
        st_clean = status_str.strip().upper()
        q = q.filter(func.upper(models.AuditLogs.status) == st_clean)

    if date_from_str and date_from_str.strip():
        try:
            dt_from = datetime.datetime.strptime(date_from_str.strip()[:10], "%Y-%m-%d")
            q = q.filter(models.AuditLogs.created_at >= dt_from)
        except ValueError:
            pass

    if date_to_str and date_to_str.strip():
        try:
            dt_to = datetime.datetime.strptime(date_to_str.strip()[:10], "%Y-%m-%d") + datetime.timedelta(days=1)
            q = q.filter(models.AuditLogs.created_at < dt_to)
        except ValueError:
            pass

    total_count = q.count()
    effective_page_size = limit_int if (limit_int is not None and limit_int > 0) else page_size_int
    offset_val = (page_int - 1) * effective_page_size

    rows = (
        q.order_by(desc(models.AuditLogs.created_at), desc(models.AuditLogs.id))
        .offset(offset_val)
        .limit(effective_page_size)
        .all()
    )

    items = []
    for row in rows:
        entry = row.AuditLogs
        resolved_name = row.name or (f"User #{entry.user_id}" if entry.user_id else "System")
        user_display = f"{resolved_name} (#{entry.user_id})" if entry.user_id else "System"
        action_plain = ACTION_PLAIN_WORDS.get(entry.activity_type, entry.activity_type.replace("_", " ").title())
        
        # Details must never contain emails
        sanitized_details = entry.details or "-"
        if "@" in sanitized_details:
            sanitized_details = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', f'User ID #{entry.user_id or "unknown"}', sanitized_details)

        items.append({
            "id": entry.id,
            "user_id": entry.user_id,
            "user_name": resolved_name,
            "user_display": user_display,
            "activity_type": entry.activity_type,
            "action_plain": action_plain,
            "file_name": entry.file_name or "—",
            "status": entry.status or "SUCCESS",
            "details": sanitized_details,
            "ip_address": entry.ip_address or "—",
            "time": entry.created_at.isoformat() if entry.created_at else None,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        })

    total_pages = max(1, math.ceil(total_count / effective_page_size)) if effective_page_size > 0 else 1

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": effective_page_size,
        "total_pages": total_pages,
        "action_categories": ["all", "sign-in", "upload", "analysis", "account"],
    }

@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    req: CreateUserRequest,
    current_admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    email = req.email.strip().lower()
    email_canonical = auth.canonicalize_email(email)
    existing = db.query(models.User).filter(
        or_(
            models.User.email_canonical == email_canonical,
            models.User.email == email
        )
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered.")

    new_user = models.User(
        name=req.name.strip(),
        email=email,
        email_canonical=email_canonical,
        password_hash=auth.hash_password(req.password),
        role=req.role,
        status="active",
        is_active=True,
        must_change_password=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    auth.record_audit_event(
        db,
        actor_id=current_admin.id,
        action="USER_CREATED",
        target=f"user:{new_user.id}",
        status="SUCCESS",
        details=f"Admin created user #{new_user.id} (role={new_user.role})"
    )

    return {
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role,
        "status": new_user.status,
        "is_active": new_user.is_active,
        "must_change_password": new_user.must_change_password
    }

@router.patch("/users/{user_id}")
def update_user_status(
    user_id: int,
    req: UpdateUserStatusRequest,
    current_admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user.id == current_admin.id and not req.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable your own admin account.")

    user.is_active = req.is_active
    user.status = "active" if req.is_active else "disabled"
    db.commit()
    action = "USER_ENABLED" if req.is_active else "USER_DISABLED"
    auth.record_audit_event(
        db,
        actor_id=current_admin.id,
        action=action,
        target=f"user:{user.id}",
        status="SUCCESS",
        details=f"Admin {'enabled' if req.is_active else 'disabled'} user #{user.id}"
    )

    return {"id": user.id, "email": user.email, "status": user.status, "is_active": user.is_active}

@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    req: ResetPasswordRequest,
    current_admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.password_hash = auth.hash_password(req.new_password)
    user.must_change_password = True
    db.commit()
    auth.record_audit_event(
        db,
        actor_id=current_admin.id,
        action="PASSWORD_CHANGED",
        target=f"user:{user.id}",
        status="SUCCESS",
        details=f"Admin reset password for user #{user.id}"
    )

    return {"message": f"Password reset for user {user.email}. User must change password on next login."}

@router.get("/login-events")
def list_login_events(
    user_id: Optional[int] = Query(None),
    success: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(models.LoginEvent)
    if user_id is not None:
        query = query.filter(models.LoginEvent.user_id == user_id)
    if success is not None:
        query = query.filter(models.LoginEvent.success == success)
    events = query.order_by(desc(models.LoginEvent.created_at)).limit(limit).all()
    return [
        {
            "id": e.id,
            "user_id": e.user_id,
            "email_attempted": e.email_attempted,
            "success": e.success,
            "ip_address": e.ip_address,
            "user_agent": e.user_agent,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]

@router.get("/analyses")
def list_all_analyses(
    user_id: Optional[int] = Query(None),
    company: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.Analysis, models.User.email, models.User.name).outerjoin(
        models.User, models.Analysis.user_id == models.User.id
    )
    if user_id is not None:
        query = query.filter(models.Analysis.user_id == user_id)
    if company:
        query = query.filter(models.Analysis.company_name.ilike(f"%{company}%"))
    rows = query.order_by(desc(models.Analysis.created_at)).limit(200).all()
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "user_email": email or "-",
            "user_name": name or "-",
            "company_name": a.company_name,
            "industry": a.industry,
            "original_filename": a.original_filename,
            "status": a.status,
            "rows_total": a.rows_total,
            "rows_calculated": a.rows_calculated,
            "total_acquisition": float(a.total_acquisition or 0),
            "total_replacement": float(a.total_replacement or 0),
            "gemini_calls": a.gemini_calls,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a, email, name in rows
    ]

@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(auth.require_admin)
):
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    total_admins = db.query(func.count(models.User.id)).filter(models.User.role == "admin").scalar() or 0
    total_login_sessions = db.query(func.count(models.LoginEvent.id)).filter(models.LoginEvent.success == True).scalar() or 0
    total_uploaded_files = db.query(func.count(models.Analysis.id)).scalar() or 0
    total_completed_analyses = db.query(func.count(models.Analysis.id)).filter(models.Analysis.status == "completed").scalar() or 0
    total_failed_analyses = db.query(func.count(models.Analysis.id)).filter(models.Analysis.status == "failed").scalar() or 0
    require_admin_approval = os.getenv("REQUIRE_ADMIN_APPROVAL", "false").strip().lower() == "true"
    pending_requests_count = db.query(func.count(models.User.id)).filter(models.User.status == "pending_approval").scalar() or 0
    is_primary = auth.is_primary_admin(current_admin)
    primary_email = auth.get_primary_admin_email()

    recent_logs = (
        db.query(models.AuditLogs, models.User.name)
        .outerjoin(models.User, models.AuditLogs.user_id == models.User.id)
        .order_by(desc(models.AuditLogs.created_at), desc(models.AuditLogs.id))
        .limit(20)
        .all()
    )
    return {
        "total_registered_users": total_users,
        "total_admins": total_admins,
        "is_primary_admin": is_primary,
        "primary_admin_email": primary_email,
        "total_login_sessions": total_login_sessions,
        "total_uploaded_files": total_uploaded_files,
        "total_completed_analyses": total_completed_analyses,
        "total_failed_analyses": total_failed_analyses,
        "require_admin_approval": require_admin_approval,
        "pending_requests_count": pending_requests_count,
        "recent_activities": [
            {
                "id": log.AuditLogs.id,
                "user_id": log.AuditLogs.user_id,
                "user_name": log.name or (f"User #{log.AuditLogs.user_id}" if log.AuditLogs.user_id else "System"),
                "user_display": f"{log.name} (#{log.AuditLogs.user_id})" if log.AuditLogs.user_id and log.name else (f"User #{log.AuditLogs.user_id}" if log.AuditLogs.user_id else "System"),
                "activity_type": log.AuditLogs.activity_type,
                "action_plain": ACTION_PLAIN_WORDS.get(log.AuditLogs.activity_type, log.AuditLogs.activity_type.replace("_", " ").title()),
                "file_name": log.AuditLogs.file_name or "—",
                "status": log.AuditLogs.status or "SUCCESS",
                "details": re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', f'User ID #{log.AuditLogs.user_id or "unknown"}', log.AuditLogs.details or "-"),
                "ip_address": log.AuditLogs.ip_address or "—",
                "time": log.AuditLogs.created_at.isoformat() if log.AuditLogs.created_at else None,
                "created_at": log.AuditLogs.created_at.isoformat() if log.AuditLogs.created_at else None,
            }
            for log in recent_logs
        ]
    }

@router.get("/usage")
def get_user_usage(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    usage = []
    for u in users:
        analyses_count = db.query(func.count(models.Analysis.id)).filter(models.Analysis.user_id == u.id).scalar() or 0
        total_rows = db.query(func.sum(models.Analysis.rows_total)).filter(models.Analysis.user_id == u.id).scalar() or 0
        total_gemini = db.query(func.sum(models.Analysis.gemini_calls)).filter(models.Analysis.user_id == u.id).scalar() or 0
        usage.append({
            "user_id": u.id,
            "name": u.name,
            "email": u.email,
            "analyses_count": analyses_count,
            "total_rows": int(total_rows),
            "total_gemini_calls": int(total_gemini),
        })
    return usage


@router.get("/column-aliases")
def list_column_aliases(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    q = db.query(models.ColumnAliasCache, models.User.name).outerjoin(
        models.User, models.ColumnAliasCache.submitted_by == models.User.id
    )
    if status_filter:
        q = q.filter(models.ColumnAliasCache.status == status_filter)
    rows = q.order_by(desc(models.ColumnAliasCache.created_at)).all()
    return [
        {
            "id": alias.id,
            "header_hash": alias.header_hash,
            "original_header": alias.original_header or alias.normalized_header,
            "normalized_header": alias.normalized_header,
            "canonical_field": alias.canonical_field,
            "status": alias.status,
            "sample_values": [],  # Never expose raw user file values
            "validation_summary": alias.validation_summary or ("100% valid, tested" if alias.validation_passed else "Pending validation"),
            "validation_passed": bool(alias.validation_passed),
            "submitted_by": alias.submitted_by,
            "submitted_by_name": name or ("System" if not alias.submitted_by else f"User #{alias.submitted_by}"),
            "submitted_by_display": f"{name} (#{alias.submitted_by})" if alias.submitted_by and name else (f"User #{alias.submitted_by}" if alias.submitted_by else "System"),
            "approved_by": alias.approved_by,
            "created_at": alias.created_at.isoformat() if alias.created_at else None,
        }
        for alias, name in rows
    ]


@router.post("/column-aliases/{alias_id}/approve")
def approve_column_alias(
    alias_id: int,
    current_admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    from column_mapper import CANONICAL_FIELDS, save_alias_cache

    alias = db.query(models.ColumnAliasCache).filter(models.ColumnAliasCache.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column alias not found.")

    alias.status = "approved"
    alias.validation_passed = True
    if not alias.validation_summary:
        alias.validation_summary = "100% valid, admin approved"
    alias.approved_by = current_admin.id
    db.commit()
    db.refresh(alias)

    # Audit log entry (user ids only! NO emails!)
    auth.record_audit_event(
        db,
        actor_id=current_admin.id,
        action="COLUMN_ALIAS_APPROVED",
        target=f"alias_id:{alias.id}",
        user_email=None,
        status="SUCCESS",
        details=f"Admin #{current_admin.id} approved column alias #{alias.id} ('{alias.original_header or alias.normalized_header}' -> {alias.canonical_field})"
    )

    if alias.canonical_field in CANONICAL_FIELDS:
        if alias.normalized_header not in CANONICAL_FIELDS[alias.canonical_field]:
            CANONICAL_FIELDS[alias.canonical_field].append(alias.normalized_header)
        if alias.canonical_field == "major_category" and alias.normalized_header not in CANONICAL_FIELDS.get("category", []):
            CANONICAL_FIELDS["category"].append(alias.normalized_header)
        save_alias_cache()

    return {
        "message": f"Column alias '{alias.original_header or alias.normalized_header}' approved for {alias.canonical_field}.",
        "id": alias.id,
        "status": alias.status
    }


@router.post("/column-aliases/{alias_id}/reject")
def reject_column_alias(
    alias_id: int,
    current_admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    from column_mapper import CANONICAL_FIELDS, save_alias_cache

    alias = db.query(models.ColumnAliasCache).filter(models.ColumnAliasCache.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column alias not found.")

    alias.status = "rejected"
    alias.approved_by = current_admin.id
    db.commit()

    # Audit log entry (user ids only! NO emails!)
    auth.record_audit_event(
        db,
        actor_id=current_admin.id,
        action="COLUMN_ALIAS_REJECTED",
        target=f"alias_id:{alias.id}",
        user_email=None,
        status="SUCCESS",
        details=f"Admin #{current_admin.id} rejected column alias #{alias.id} ('{alias.original_header or alias.normalized_header}' -> {alias.canonical_field})"
    )

    if alias.canonical_field in CANONICAL_FIELDS and alias.normalized_header in CANONICAL_FIELDS[alias.canonical_field]:
        CANONICAL_FIELDS[alias.canonical_field] = [
            a for a in CANONICAL_FIELDS[alias.canonical_field] if a != alias.normalized_header
        ]
        save_alias_cache()

    return {
        "message": f"Column alias '{alias.original_header or alias.normalized_header}' rejected.",
        "id": alias.id,
        "status": alias.status
    }


@router.delete("/column-aliases/{alias_id}")
def remove_column_alias(
    alias_id: int,
    current_admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    """Remove a custom column alias and record an audit log (user IDs only)."""
    from column_mapper import CANONICAL_FIELDS, save_alias_cache

    alias = db.query(models.ColumnAliasCache).filter(models.ColumnAliasCache.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column alias not found.")

    norm_h = alias.normalized_header
    canon_f = alias.canonical_field
    orig_h = alias.original_header or alias.normalized_header

    # Clean in-memory cache
    if canon_f in CANONICAL_FIELDS and norm_h in CANONICAL_FIELDS[canon_f]:
        CANONICAL_FIELDS[canon_f] = [a for a in CANONICAL_FIELDS[canon_f] if a != norm_h]
    if canon_f == "major_category" and norm_h in CANONICAL_FIELDS.get("category", []):
        CANONICAL_FIELDS["category"] = [a for a in CANONICAL_FIELDS["category"] if a != norm_h]
    save_alias_cache()

    db.delete(alias)
    db.commit()

    # Audit log entry (user ids only! NO emails!)
    auth.record_audit_event(
        db,
        actor_id=current_admin.id,
        action="COLUMN_ALIAS_REMOVED",
        target=f"alias_id:{alias_id}",
        user_email=None,
        status="SUCCESS",
        details=f"Admin #{current_admin.id} removed column alias #{alias_id} ('{orig_h}' -> {canon_f})"
    )

    return {
        "message": f"Column alias '{orig_h}' removed successfully.",
        "id": alias_id,
        "status": "removed"
    }

