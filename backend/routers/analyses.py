import os
import io
import math
import hashlib
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from database import get_db
import models
from auth import get_current_active_user, record_audit_event
from report_generator import generate_excel_report_stream
from pdf_summary_generator import generate_pdf_summary_stream

router = APIRouter(prefix="/analyses", tags=["analyses"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_master_version_hash() -> str:
    """Computes SHA-256 of the active WPI master dataset file including RULES sheet."""
    master_path = os.path.join(BASE_DIR, "data", "WPI_MASTER_DATASET_CATEGORYWISE_v6.xlsx")
    if not os.path.exists(master_path):
        master_path = os.path.join(BASE_DIR, "data", "WPI_MASTER_DATASET_CATEGORYWISE.xlsx")
    if not os.path.exists(master_path):
        return "unknown"
    h = hashlib.sha256()
    with open(master_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    # Also incorporate active Building and Land method to guarantee cache invalidation on rule changes
    try:
        import calculator
        rules_sig = f":rule_{getattr(calculator, 'BUILDING_AND_LAND_METHOD', 'compound')}:{getattr(calculator, 'BUILDING_ESCALATION_RATE', 0.05)}:{getattr(calculator, 'LAND_ESCALATION_RATE', 0.05)}:{getattr(calculator, 'REFERENCE_YEAR', 2025)}"
        h.update(rules_sig.encode("utf-8"))
    except Exception:
        pass
    return h.hexdigest()

@router.get("", response_model=dict)
def get_user_analyses(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List the current user's analyses, newest first."""
    analyses = db.query(models.Analysis).filter(
        models.Analysis.user_id == current_user.id
    ).order_by(models.Analysis.created_at.desc()).all()

    results = []
    for a in analyses:
        results.append({
            "id": a.id,
            "company_name": a.company_name or "",
            "industry": a.industry or "",
            "original_filename": a.original_filename,
            "status": a.status,
            "rows_total": a.rows_total or 0,
            "rows_calculated": a.rows_calculated or 0,
            "rows_manual_review": a.rows_manual_review or 0,
            "rows_not_applicable": a.rows_not_applicable or 0,
            "total_acquisition": float(a.total_acquisition or 0),
            "total_replacement": float(a.total_replacement or 0),
            "master_version": a.master_version[:8] if a.master_version else "",
            "gemini_calls": a.gemini_calls or 0,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None
        })
    return {"analyses": results}

@router.get("/latest", response_model=dict)
def get_latest_user_analysis(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve the user's latest completed analysis."""
    latest = db.query(models.Analysis).filter(
        models.Analysis.user_id == current_user.id,
        models.Analysis.status == "completed"
    ).order_by(models.Analysis.created_at.desc()).first()

    if not latest:
        return {"analysis": None}

    return {
        "analysis": {
            "id": latest.id,
            "company_name": latest.company_name or "",
            "industry": latest.industry or "",
            "original_filename": latest.original_filename,
            "status": latest.status,
            "rows_total": latest.rows_total or 0,
            "rows_calculated": latest.rows_calculated or 0,
            "rows_manual_review": latest.rows_manual_review or 0,
            "rows_not_applicable": latest.rows_not_applicable or 0,
            "total_acquisition": float(latest.total_acquisition or 0),
            "total_replacement": float(latest.total_replacement or 0),
            "master_version": latest.master_version[:8] if latest.master_version else "",
            "gemini_calls": latest.gemini_calls or 0,
            "created_at": latest.created_at.isoformat() if latest.created_at else None,
            "completed_at": latest.completed_at.isoformat() if latest.completed_at else None
        }
    }

@router.post("/check-duplicate")
async def check_duplicate_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Checks if the uploaded file has already been analyzed by this user with the current master version."""
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "25"))
    max_bytes = max_mb * 1024 * 1024
    total_bytes = 0
    chunks = []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum allowed upload size of {max_mb} MB."
            )
        chunks.append(chunk)
    content = b"".join(chunks)
    await file.seek(0)
    file_sha256 = hashlib.sha256(content).hexdigest()
    master_version = get_master_version_hash()

    existing = db.query(models.Analysis).filter(
        models.Analysis.user_id == current_user.id,
        models.Analysis.file_sha256 == file_sha256,
        models.Analysis.master_version == master_version,
        models.Analysis.status == "completed"
    ).order_by(models.Analysis.created_at.desc()).first()

    if existing:
        return {
            "duplicate_found": True,
            "analysis": {
                "id": existing.id,
                "company_name": existing.company_name or "",
                "original_filename": existing.original_filename,
                "created_at": existing.created_at.isoformat() if existing.created_at else None,
                "master_version": existing.master_version[:8] if existing.master_version else "",
                "rows_total": existing.rows_total or 0,
                "total_acquisition": float(existing.total_acquisition or 0),
                "total_replacement": float(existing.total_replacement or 0)
            }
        }
    return {"duplicate_found": False, "analysis": None}

@router.get("/{analysis_id}")
def get_analysis_details(
    analysis_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get single analysis details. Returns 404 for another user's analysis."""
    analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
    if not analysis or (analysis.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    return {
        "id": analysis.id,
        "company_name": analysis.company_name or "",
        "industry": analysis.industry or "",
        "original_filename": analysis.original_filename,
        "status": analysis.status,
        "rows_total": analysis.rows_total or 0,
        "rows_calculated": analysis.rows_calculated or 0,
        "rows_manual_review": analysis.rows_manual_review or 0,
        "rows_not_applicable": analysis.rows_not_applicable or 0,
        "total_acquisition": float(analysis.total_acquisition or 0),
        "total_replacement": float(analysis.total_replacement or 0),
        "master_version": analysis.master_version[:8] if analysis.master_version else "",
        "gemini_calls": analysis.gemini_calls or 0,
        "error_message": analysis.error_message,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None
    }

@router.get("/{analysis_id}/summary")
def get_analysis_summary(
    analysis_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Calculates dashboard summary metrics for an analysis. Returns 404 for unauthorized users."""
    analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
    if not analysis or (analysis.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    # Aggregations from analysis_rows
    wpi_groups = db.query(
        models.AnalysisRow.wpi_group, func.count(models.AnalysisRow.id)
    ).filter(models.AnalysisRow.analysis_id == analysis_id).group_by(models.AnalysisRow.wpi_group).all()

    major_cats = db.query(
        models.AnalysisRow.major_category, func.count(models.AnalysisRow.id)
    ).filter(
        models.AnalysisRow.analysis_id == analysis_id,
        models.AnalysisRow.major_category.isnot(None),
        models.AnalysisRow.major_category != ""
    ).group_by(models.AnalysisRow.major_category).all()

    sub_cats = db.query(
        models.AnalysisRow.sub_category, func.count(models.AnalysisRow.id)
    ).filter(
        models.AnalysisRow.analysis_id == analysis_id,
        models.AnalysisRow.sub_category.isnot(None),
        models.AnalysisRow.sub_category != ""
    ).group_by(models.AnalysisRow.sub_category).all()

    locations = db.query(
        models.AnalysisRow.location, func.count(models.AnalysisRow.id)
    ).filter(
        models.AnalysisRow.analysis_id == analysis_id,
        models.AnalysisRow.location.isnot(None),
        models.AnalysisRow.location != ""
    ).group_by(models.AnalysisRow.location).all()

    manual_breakdown = db.query(
        models.AnalysisRow.note, func.count(models.AnalysisRow.id)
    ).filter(
        models.AnalysisRow.analysis_id == analysis_id,
        or_(
            models.AnalysisRow.status == 'Manual Review Required',
            models.AnalysisRow.status.like('%Manual%'),
            models.AnalysisRow.status.like('%Failed%'),
            models.AnalysisRow.status == 'Needs Mapping'
        )
    ).group_by(models.AnalysisRow.note).all()

    total_acq = float(analysis.total_acquisition or 0.0)
    total_rep = float(analysis.total_replacement or 0.0)

    return {
        "Total Assets": analysis.rows_total or 0,
        "Calculated Assets": analysis.rows_calculated or 0,
        "Manual Review Count": analysis.rows_manual_review or 0,
        "Not Applicable Count": analysis.rows_not_applicable or 0,
        "Total Acquisition Value": total_acq,
        "Total Replacement Value": total_rep,
        "Total Difference": total_rep - total_acq,
        "Overall Increase %": ((total_rep - total_acq) / total_acq) if total_acq > 0 else 0.0,
        "Assets by WPI Category": {k or "Unassigned": v for k, v in wpi_groups},
        "Assets by Major Category": {k: v for k, v in major_cats},
        "Assets by Sub Category": {k: v for k, v in sub_cats},
        "Assets by Plant/Location": {k: v for k, v in locations},
        "Manual Review Breakdown": {k or "Review Required": v for k, v in manual_breakdown},
        "downloadUrl": f"/analyses/{analysis.id}/download"
    }

@router.get("/{analysis_id}/rows")
def get_analysis_rows(
    analysis_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    row_status: Optional[str] = Query(None, alias="status"),
    wpi_group: Optional[str] = Query(None),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Server-side paginated, searchable and filterable rows for an analysis. Returns 404 for unauthorized users."""
    analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
    if not analysis or (analysis.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    query = db.query(models.AnalysisRow).filter(models.AnalysisRow.analysis_id == analysis_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.AnalysisRow.description.ilike(term),
                models.AnalysisRow.asset_code.ilike(term),
                models.AnalysisRow.major_category.ilike(term),
                models.AnalysisRow.sub_category.ilike(term)
            )
        )

    if row_status and row_status.strip():
        if row_status.strip().lower() == "calculated":
            query = query.filter(
                or_(
                    models.AnalysisRow.status == "Success",
                    models.AnalysisRow.calculation_method.like("%Compound%"),
                    models.AnalysisRow.calculation_method.like("%WPI%"),
                    models.AnalysisRow.calculation_method.like("%Escalation%"),
                    models.AnalysisRow.calculation_method.like("%At Cost%")
                )
            )
        elif row_status.strip().lower() == "manual":
            query = query.filter(
                or_(
                    models.AnalysisRow.status == 'Manual Review Required',
                    models.AnalysisRow.status.like('%Manual%'),
                    models.AnalysisRow.status.like('%Failed%'),
                    models.AnalysisRow.status == 'Needs Mapping'
                )
            )
        elif row_status.strip().lower() == "na":
            query = query.filter(models.AnalysisRow.status.like('%Not Applicable%'))
        else:
            query = query.filter(models.AnalysisRow.status == row_status.strip())

    if wpi_group and wpi_group.strip():
        query = query.filter(models.AnalysisRow.wpi_group == wpi_group.strip())

    total = query.count()
    rows = query.order_by(models.AnalysisRow.row_no.asc()).offset((page - 1) * page_size).limit(page_size).all()

    formatted_rows = []
    for r in rows:
        formatted_rows.append({
            "id": r.id,
            "rowNo": r.row_no,
            "assetCode": r.asset_code or "-",
            "description": r.description or "",
            "capDate": r.capitalized_date or "-",
            "purchaseYear": r.purchase_year,
            "acquisitionValue": float(r.acquisition_value) if r.acquisition_value is not None else 0.0,
            "accumDep": float(r.accumulated_dep) if r.accumulated_dep is not None else 0.0,
            "bookValue": float(r.book_value) if r.book_value is not None else 0.0,
            "majorCategory": r.major_category or "-",
            "subCategory": r.sub_category or "-",
            "assetClass": r.asset_class or "-",
            "location": r.location or "-",
            "wpiGroup": r.wpi_group or "-",
            "purchaseWpi": float(r.purchase_wpi) if r.purchase_wpi is not None else None,
            "currentWpi": float(r.current_wpi) if r.current_wpi is not None else None,
            "replacementValue": float(r.replacement_value) if r.replacement_value is not None else 0.0,
            "difference": float(r.difference) if r.difference is not None else 0.0,
            "increasePct": float(r.increase_pct) if r.increase_pct is not None else None,
            "calculationMethod": r.calculation_method or "-",
            "status": r.status or "-",
            "note": r.note or ""
        })

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "rows": formatted_rows
    }

def check_analysis_view_permission(analysis: models.Analysis, current_user: models.User):
    """Enforces: owner only, admin only if ADMIN_CAN_VIEW_ROWS is true."""
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if analysis.user_id == current_user.id:
        return
    if current_user.role == "admin":
        admin_can_view = os.getenv("ADMIN_CAN_VIEW_ROWS", "false").strip().lower() in ("true", "1", "yes")
        if not admin_can_view:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access to user data rows is restricted"
            )
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

@router.get("/{analysis_id}/download")
def download_analysis_report(
    analysis_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Builds the Excel report ON-DEMAND from saved rows. Zero files saved to disk. Returns 404 for unauthorized users."""
    analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
    check_analysis_view_permission(analysis, current_user)

    rows = db.query(models.AnalysisRow).filter(
        models.AnalysisRow.analysis_id == analysis_id
    ).order_by(models.AnalysisRow.row_no.asc()).all()

    excel_stream = generate_excel_report_stream(analysis, rows)
    safe_name = (analysis.company_name or "FAR").replace(" ", "_")
    filename = f"FAR_Replacement_Report_{safe_name}_{analysis.id}.xlsx"

    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/{analysis_id}/summary.pdf")
def download_analysis_summary_pdf(
    analysis_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Builds the Valuation Summary PDF report ON-DEMAND from saved analysis_rows with SQL grouping.
    No recalculation, no Gemini calls, and zero files stored on disk.
    Permissions: Owner only, or admin only if ADMIN_CAN_VIEW_ROWS is true.
    """
    analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
    check_analysis_view_permission(analysis, current_user)

    pdf_stream = generate_pdf_summary_stream(analysis, db)
    safe_name = (analysis.company_name or "FAR").replace(" ", "_")
    filename = f"Valuation_Summary_{safe_name}_{analysis.id}.pdf"

    return StreamingResponse(
        pdf_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.delete("/{analysis_id}")
def delete_analysis(
    analysis_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deletes an analysis and cascade deletes all its rows. Returns 404 for unauthorized users."""
    analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
    if not analysis or (analysis.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    record_audit_event(db, actor_id=current_user.id, action="analysis_deleted", target=f"analysis_{analysis_id}")
    db.delete(analysis)
    db.commit()

    return {"message": "Analysis deleted successfully", "id": analysis_id}
