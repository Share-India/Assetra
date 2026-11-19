import os
import shutil
import uuid
import time
import logging
import json
import threading
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from calculator import process_file, load_datasets, CATEGORY_CACHE, save_category_cache, VALID_WPI_GROUPS
from dotenv import load_dotenv
import requests
import math

def extract_original_row_dict(raw, headers):
    """Converts a raw row list or dict into a dictionary keyed by column headers."""
    orig_dict = {}
    if isinstance(raw, list):
        for col_idx, col_name in enumerate(headers):
            if col_idx < len(raw):
                val = raw[col_idx]
                if val is not None:
                    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                        continue
                    if isinstance(val, (datetime.date, datetime.datetime)):
                        orig_dict[col_name] = val.isoformat()
                    else:
                        orig_dict[col_name] = val
    elif isinstance(raw, dict):
        orig_dict = raw
    return orig_dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=env_path)

# ==============================================================================
# SECURE LOGGING CONFIGURATION (RotatingFileHandler: logs/app.log & logs/error.log)
# ==============================================================================
from contextlib import asynccontextmanager
from logger_config import setup_logging, SafeLogFilter

logger = setup_logging()

# Read CORS allowed origins from FRONTEND_URL in .env (no '*' wildcard)
raw_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
allowed_origins = [
    o.strip().rstrip("/")
    for o in raw_frontend_url.split(",")
    if o.strip() and o.strip() != "*"
]
if not allowed_origins:
    allowed_origins = ["http://localhost:3000"]

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
MAX_ROWS_PER_FILE = int(os.getenv("MAX_ROWS_PER_FILE", "30000"))
DAILY_ANALYSES_PER_USER = int(os.getenv("DAILY_ANALYSES_PER_USER", "5"))
MONTHLY_GEMINI_CALLS_PER_USER = int(os.getenv("MONTHLY_GEMINI_CALLS_PER_USER", "500"))
MONTHLY_GEMINI_CALLS_GLOBAL = int(os.getenv("MONTHLY_GEMINI_CALLS_GLOBAL", "20000"))

def validate_production_smtp_configuration():
    """In production mode, refuse to start if SMTP is not configured."""
    env = os.getenv("ENV", "development").strip().lower()
    if env == "production":
        smtp_host = os.getenv("SMTP_HOST", "").strip()
        smtp_user = os.getenv("SMTP_USER", "").strip()
        smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
        if not smtp_host or not smtp_user or not smtp_pass:
            logger.critical("FATAL: SMTP is not configured in production mode (ENV=production). Refusing to start.")
            raise RuntimeError("SMTP is not configured in production mode. Refusing to start.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler logging application startup and shutdown."""
    validate_production_smtp_configuration()
    await run_startup_diagnostics()
    try:
        yield
    finally:
        logger.info("[BACKEND] Shutting down FAR Calculator Backend gracefully.")

# ==============================================================================
# APP INITIALIZATION & CORS
# ==============================================================================
app = FastAPI(title="ASSETRA Replacement Value Calculator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers.auth import router as auth_router
from routers.admin import router as admin_router
from routers.analyses import router as analyses_router, get_master_version_hash
from routers.account import router as account_router
from auth import get_current_active_user, record_audit_event
import models
from database import SessionLocal
import hashlib
import datetime

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(analyses_router)
app.include_router(account_router)

@app.middleware("http")
async def log_requests_and_add_no_cache_headers(request, call_next):
    start_ts = time.perf_counter()
    path = request.url.path
    method = request.method
    client_ip = request.client.host if request.client else "unknown"
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_ts) * 1000.0
        logger.exception(
            f"[API ERROR] Unhandled exception on {method} {path} from {client_ip} ({duration_ms:.1f}ms): {type(exc).__name__}: {exc}"
        )
        raise

    duration_ms = (time.perf_counter() - start_ts) * 1000.0
    status_code = response.status_code
    if status_code >= 500:
        logger.error(f"[API] {method} {path} -> {status_code} ({duration_ms:.1f}ms) [ip={client_ip}]")
    elif status_code >= 400:
        logger.warning(f"[API] {method} {path} -> {status_code} ({duration_ms:.1f}ms) [ip={client_ip}]")
    else:
        logger.info(f"[API] {method} {path} -> {status_code} ({duration_ms:.1f}ms)")

    if path.startswith("/auth") or path.startswith("/analyses") or path.startswith("/admin") or path.startswith("/account"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
app.mount("/downloads", StaticFiles(directory=DOWNLOADS_DIR), name="downloads")

# ==============================================================================
# DOWNLOADS CLEANUP
# ==============================================================================
def cleanup_old_downloads(days: int = 7):
    """Deletes files in DOWNLOADS_DIR older than the specified number of days."""
    if not os.path.exists(DOWNLOADS_DIR):
        return
    now = time.time()
    cutoff_seconds = days * 86400
    cleaned_count = 0
    try:
        for filename in os.listdir(DOWNLOADS_DIR):
            file_path = os.path.join(DOWNLOADS_DIR, filename)
            if os.path.isfile(file_path):
                try:
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > cutoff_seconds:
                        os.remove(file_path)
                        cleaned_count += 1
                except Exception as err:
                    logger.warning(f"Failed to remove expired file {file_path}: {err}")
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} download file(s) older than {days} days.")
    except Exception as e:
        logger.error(f"Error during downloads cleanup: {e}")

async def save_upload_file_safe(file: UploadFile, dest_path: str, max_mb: int = MAX_UPLOAD_MB) -> int:
    """Streams and saves uploaded file while enforcing maximum upload size."""
    max_bytes = max_mb * 1024 * 1024
    total_bytes = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    with open(dest_path, "wb") as buffer:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                buffer.close()
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except Exception:
                        pass
                logger.error(f"Upload failed for '{file.filename}': file exceeds maximum size of {max_mb} MB.")
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum allowed upload size of {max_mb} MB."
                )
            buffer.write(chunk)
    return total_bytes

async def read_upload_file_safe(file: UploadFile, max_mb: int = MAX_UPLOAD_MB) -> bytes:
    """Streams uploaded file into memory while enforcing maximum upload size."""
    max_bytes = max_mb * 1024 * 1024
    total_bytes = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    chunks = []
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            logger.error(f"Upload failed for '{file.filename}': file exceeds maximum size of {max_mb} MB.")
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum allowed upload size of {max_mb} MB."
            )
        chunks.append(chunk)
    return b"".join(chunks)

# ==============================================================================
# BACKGROUND JOB MANAGEMENT
# ==============================================================================
JOBS = {}
JOBS_LOCK = threading.Lock()

def calculation_worker(
    job_id: str,
    temp_path: str,
    wpi_group: str,
    user_mapping_dict: dict,
    header_row_idx: int,
    sheet_name: str,
    analysis_id: int = None
):
    """Worker thread that executes long-running process_file in the background and saves rows to MySQL."""
    logger.info(f"Starting background calculation worker for Job ID: {job_id} (Analysis ID: {analysis_id})")
    try:
        def progress_cb(pct: int, msg: str):
            with JOBS_LOCK:
                if job_id in JOBS:
                    JOBS[job_id]["progress"] = int(pct * 0.95) if analysis_id else pct
                    JOBS[job_id]["message"] = msg
                    JOBS[job_id]["status"] = "processing"
                    JOBS[job_id]["updated_at"] = time.time()

        result = process_file(
            temp_path,
            wpi_group,
            user_mapping_dict,
            header_row_idx,
            sheet_name,
            progress_callback=progress_cb
        )

        if analysis_id:
            with JOBS_LOCK:
                if job_id in JOBS:
                    JOBS[job_id]["progress"] = 96
                    JOBS[job_id]["message"] = "Saving result rows to database..."

            db = SessionLocal()
            try:
                analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
                if analysis:
                    metrics = result.get("metrics", {})
                    mapped_data = result.get("mappedData", [])
                    headers = result.get("headers", [])

                    analysis.columns_order = headers
                    analysis.rows_total = metrics.get("Total Assets", len(mapped_data))
                    analysis.rows_calculated = metrics.get("Calculated Assets", 0)
                    analysis.rows_manual_review = metrics.get("Manual Review Count", 0)
                    analysis.rows_not_applicable = metrics.get("Not Applicable Count", 0)
                    analysis.total_acquisition = metrics.get("Total Acquisition Value", 0.0)
                    analysis.total_replacement = metrics.get("Total Replacement Value", 0.0)
                    analysis.gemini_calls = metrics.get("gemini_calls", 0)

                    BATCH_SIZE = 1000
                    for i in range(0, len(mapped_data), BATCH_SIZE):
                        chunk = mapped_data[i:i + BATCH_SIZE]
                        row_models = []
                        for idx_in_chunk, r in enumerate(chunk):
                            row_no = i + idx_in_chunk + 1
                            acq_val = r.get("acquisitionValue")
                            diff_val = r.get("difference")
                            inc_pct = None
                            if acq_val and diff_val is not None:
                                try:
                                    inc_pct = float(diff_val) / float(acq_val)
                                except Exception:
                                    inc_pct = 0.0
                            elif r.get("status") in ["Success", "Not Applicable"]:
                                inc_pct = 0.0

                            row_models.append(
                                models.AnalysisRow(
                                    analysis_id=analysis_id,
                                    row_no=row_no,
                                    asset_code=str(r.get("assetCode") or "") if r.get("assetCode") is not None else None,
                                    description=str(r.get("description") or "") if r.get("description") is not None else None,
                                    capitalized_date=str(r.get("capDate") or "") if r.get("capDate") is not None else None,
                                    purchase_year=r.get("purchaseYear") if isinstance(r.get("purchaseYear"), int) else None,
                                    acquisition_value=acq_val if isinstance(acq_val, (int, float)) else None,
                                    accumulated_dep=r.get("accumDep") if isinstance(r.get("accumDep"), (int, float)) else None,
                                    book_value=r.get("bookValue") if isinstance(r.get("bookValue"), (int, float)) else None,
                                    major_category=str(r.get("majorCategory") or "") if r.get("majorCategory") is not None else None,
                                    sub_category=str(r.get("subCategory") or "") if r.get("subCategory") is not None else None,
                                    asset_class=str(r.get("assetClass") or "") if r.get("assetClass") is not None else None,
                                    location=str(r.get("location") or "") if r.get("location") is not None else None,
                                    wpi_group=str(r.get("wpiGroup") or "") if r.get("wpiGroup") is not None else None,
                                    wpi_series="SERIES_2011-12" if r.get("calculationMethod") == "WPI Based" else None,
                                    purchase_wpi=r.get("purchaseWpi") if isinstance(r.get("purchaseWpi"), (int, float)) else None,
                                    current_wpi=r.get("currentWpi") if isinstance(r.get("currentWpi"), (int, float)) else None,
                                    calculation_method=str(r.get("calculationMethod") or "") if r.get("calculationMethod") is not None else None,
                                    status=str(r.get("status") or "") if r.get("status") is not None else None,
                                    note=str(r.get("note") or "") if r.get("note") is not None else None,
                                    replacement_value=r.get("replacementValue") if isinstance(r.get("replacementValue"), (int, float)) else None,
                                    difference=diff_val if isinstance(diff_val, (int, float)) else None,
                                    increase_pct=inc_pct,
                                    original_row=extract_original_row_dict(r.get("rawRow"), headers)
                                )
                            )
                        db.bulk_save_objects(row_models)
                        db.commit()

                    analysis.status = "completed"
                    analysis.completed_at = datetime.datetime.utcnow()
                    db.commit()
                    record_audit_event(
                        db,
                        actor_id=analysis.user_id,
                        action="ANALYSIS_COMPLETED",
                        target=f"analysis:{analysis.id}:{analysis.original_filename}",
                        file_name=analysis.original_filename,
                        status="SUCCESS",
                        details=f"Analysis #{analysis.id} completed ({analysis.rows_calculated}/{analysis.rows_total} rows calculated)"
                    )

                    result["analysis_id"] = analysis_id
                    result["metrics"]["downloadUrl"] = f"/analyses/{analysis_id}/download"
            except Exception as save_err:
                logger.exception(f"Failed to persist rows for analysis {analysis_id}: {save_err}")
                db.rollback()
                if analysis:
                    analysis.status = "failed"
                    analysis.error_message = f"Failed to save result rows: {str(save_err)}"
                    db.commit()
                    record_audit_event(
                        db,
                        actor_id=analysis.user_id,
                        action="ANALYSIS_FAILED",
                        target=f"analysis:{analysis.id}:{analysis.original_filename}",
                        file_name=analysis.original_filename,
                        status="FAILED",
                        details=f"Failed to save result rows for analysis #{analysis.id}: {str(save_err)}"
                    )
                raise save_err
            finally:
                db.close()

        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]["status"] = "completed"
                JOBS[job_id]["progress"] = 100
                JOBS[job_id]["message"] = "Calculation complete."
                JOBS[job_id]["result"] = result
                if analysis_id:
                    JOBS[job_id]["analysis_id"] = analysis_id
                JOBS[job_id]["updated_at"] = time.time()

        logger.info(f"Background calculation worker for Job ID: {job_id} COMPLETED successfully.")
    except Exception as e:
        logger.exception(f"Background calculation worker for Job ID: {job_id} FAILED: {e}")
        if analysis_id:
            db_err_sess = SessionLocal()
            try:
                failed_analysis = db_err_sess.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
                if failed_analysis and failed_analysis.status != "failed":
                    failed_analysis.status = "failed"
                    failed_analysis.error_message = str(e)
                    db_err_sess.commit()
                    record_audit_event(
                        db_err_sess,
                        actor_id=failed_analysis.user_id,
                        action="ANALYSIS_FAILED",
                        target=f"analysis:{failed_analysis.id}:{failed_analysis.original_filename}",
                        file_name=failed_analysis.original_filename,
                        status="FAILED",
                        details=f"Analysis #{failed_analysis.id} calculation failed: {str(e)}"
                    )
            except Exception as inner_err:
                logger.error(f"Could not mark analysis {analysis_id} as failed: {inner_err}")
            finally:
                db_err_sess.close()
        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]["status"] = "failed"
                JOBS[job_id]["error"] = str(e)
                JOBS[job_id]["message"] = f"Calculation failed: {str(e)}"
                JOBS[job_id]["updated_at"] = time.time()
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        # Clean any stray excel files in downloads to satisfy Ground Rule 2
        for f in os.listdir(DOWNLOADS_DIR):
            if f.endswith(".xlsx"):
                try:
                    os.remove(os.path.join(DOWNLOADS_DIR, f))
                except Exception:
                    pass
        if os.path.exists("WPI_Validation_Report.xlsx"):
            try:
                os.remove("WPI_Validation_Report.xlsx")
            except Exception:
                pass

# ==============================================================================
# STARTUP & HEALTH
# ==============================================================================
def _get_listening_host_port() -> tuple[str, int]:
    """Determine the real host and port the server is listening on."""
    import inspect
    import sys

    found_host = None
    found_port = None

    frame = inspect.currentframe()
    try:
        while frame is not None:
            sockets = frame.f_locals.get("sockets")
            if isinstance(sockets, (list, tuple)) and sockets:
                try:
                    sockname = sockets[0].getsockname()
                    if isinstance(sockname, tuple) and len(sockname) >= 2:
                        return str(sockname[0]), int(sockname[1])
                except Exception:
                    pass
            if found_port is None:
                obj = frame.f_locals.get("self")
                cfg = getattr(obj, "config", None)
                if cfg is not None and hasattr(cfg, "port") and hasattr(cfg, "host"):
                    try:
                        found_host = str(cfg.host)
                        found_port = int(cfg.port)
                    except Exception:
                        pass
            frame = frame.f_back
    finally:
        del frame

    if found_port is not None:
        return found_host or "127.0.0.1", found_port

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg in ("--port", "-p") and i + 1 < len(argv):
            try:
                port = int(argv[i + 1])
            except ValueError:
                pass
        elif arg.startswith("--port="):
            try:
                port = int(arg.split("=", 1)[1])
            except ValueError:
                pass
        elif arg == "--host" and i + 1 < len(argv):
            host = argv[i + 1]
        elif arg.startswith("--host="):
            host = arg.split("=", 1)[1]

    return host, port


async def run_startup_diagnostics():
    from sqlalchemy import text
    from database import engine, DB_HOST, DB_NAME

    logger.info("[BACKEND] Starting FAR Calculator Backend...")
    logger.info(f"[BACKEND] .env loaded from: {env_path} (exists: {os.path.exists(env_path)})")

    env_mode = os.getenv("ENV", "development").strip().lower() or "development"
    logger.info(f"[BACKEND] ENV: {env_mode}")

    db_connected = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        models.Base.metadata.create_all(bind=engine)
        db_connected = True
    except Exception as db_exc:
        db_connected = False
        logger.error(f"[BACKEND] Database connection check failed during startup: {db_exc}")
    logger.info(
        f"[BACKEND] Database connected: {'yes' if db_connected else 'no'} "
        f"(host: {DB_HOST}, database: {DB_NAME})"
    )

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_configured = bool(smtp_host and smtp_user and smtp_pass)
    logger.info(f"[BACKEND] SMTP configured: {'yes' if smtp_configured else 'no'}")

    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    google_configured = bool(google_client_id)
    logger.info(f"[BACKEND] Google sign-in configured: {'yes' if google_configured else 'no'}")

    email_verification_required = os.getenv("REQUIRE_EMAIL_VERIFICATION", "true").strip().lower() not in ("false", "0", "no")
    logger.info(f"[BACKEND] Email verification required: {'yes' if email_verification_required else 'no'}")

    gemini_model = os.getenv("GEMINI_MODEL", "Not Configured")
    gemini_key = os.getenv("GEMINI_API_KEY")
    logger.info(f"[BACKEND] GEMINI_MODEL: {gemini_model}")
    logger.info(f"[BACKEND] GEMINI_API_KEY: {'Configured' if gemini_key else 'Not Found'}")
    logger.info(f"[BACKEND] CORS_ORIGINS: {allowed_origins}")
    logger.info(
        f"[BACKEND] Active limits: upload_size={MAX_UPLOAD_MB} MB, "
        f"rows_per_file={MAX_ROWS_PER_FILE}, "
        f"daily_analyses={DAILY_ANALYSES_PER_USER}/day, "
        f"monthly_gemini_calls={MONTHLY_GEMINI_CALLS_PER_USER}/user ({MONTHLY_GEMINI_CALLS_GLOBAL} global)"
    )

    load_datasets()
    cleanup_old_downloads(days=7)

    try:
        import auth
        from database import SessionLocal
        with SessionLocal() as db_session:
            admin_emails = auth.get_authorized_admin_emails()
            for admin_em in admin_emails:
                u = db_session.query(models.User).filter(models.User.email == admin_em).first()
                if u:
                    auth.sync_user_admin_role(db_session, u)
            unauth_admins = db_session.query(models.User).filter(
                models.User.role == "admin",
                models.User.email.notin_(admin_emails)
            ).all()
            for u in unauth_admins:
                auth.sync_user_admin_role(db_session, u)
    except Exception as e:
        logger.warning(f"[BACKEND] Could not sync admin accounts during startup: {e}")

    listen_host, listen_port = _get_listening_host_port()
    logger.info(f"[BACKEND] Startup complete. Listening on http://{listen_host}:{listen_port}")

@app.get("/health")
def health_check():
    import calculator
    return {
        "status": "ok",
        "max_upload_mb": MAX_UPLOAD_MB,
        "active_jobs": len(JOBS),
        "wpi_master_loaded": calculator.WPI_DATA is not None
    }

# ==============================================================================
# FIXED INDUSTRY LIST (WPI Major Categories from Master File) & CACHE
# ==============================================================================
import re as _re

WPI_MAJOR_CATEGORIES_FILE = os.path.join(BASE_DIR, "data", "wpi_major_categories.json")

def load_fixed_industries() -> list[str]:
    try:
        with open(WPI_MAJOR_CATEGORIES_FILE, "r", encoding="utf-8") as f:
            items = json.load(f)
            if isinstance(items, list) and items:
                return [str(x).strip() for x in items if str(x).strip()]
    except Exception as err:
        logger.error(f"Failed to load {WPI_MAJOR_CATEGORIES_FILE}: {err}")
    return [
        "Food Articles",
        "Non-Food Articles",
        "Minerals",
        "Crude Petroleum & Natural Gas",
        "Coal",
        "Mineral Oils",
        "Electricity",
        "Manufacture of Food Products",
        "Manufacture of Beverages",
        "Manufacture of Tobacco Products",
        "Manufacture of Textiles",
        "Manufacture of Wearing Apparel",
        "Manufacture of Leather and Related Products",
        "Manufacture of Wood and of Products of Wood and Cork",
        "Manufacture of Paper and Paper Products",
        "Printing and Reproduction of Recorded Media",
        "Manufacture of Chemicals and Chemical Products",
        "Manufacture of Pharmaceuticals, Medicinal Chemical and Botanical Products",
        "Manufacture of Rubber and Plastics Products",
        "Manufacture of Other Non-Metallic Mineral Products",
        "Manufacture of Basic Metals",
        "Manufacture of Fabricated Metal Products, Except Machinery and Equipment",
        "Manufacture of Computer, Electronic and Optical Products",
        "Manufacture of Electrical Equipment",
        "Manufacture of Machinery and Equipment",
        "Manufacture of Motor Vehicles, Trailers and Semi-Trailers",
        "Manufacture of Other Transport Equipment",
        "Manufacture of Furniture",
        "Other Manufacturing"
    ]

FIXED_INDUSTRY_LIST = load_fixed_industries()

def normalize_company_name(name: str) -> str:
    return _re.sub(r"\s+", " ", (name or "").strip().lower())

@app.get("/industries")
def get_fixed_industries():
    """Return the fixed list of 29 WPI Major Category names from the master file."""
    return {
        "industries": FIXED_INDUSTRY_LIST,
        "source": "WPI Major Category names from master file (WPI_MASTER_DATASET_CATEGORYWISE_v6.xlsx)"
    }

@app.get("/suggest-industry/{company_name}")
def suggest_industry(company_name: str):
    """Suggest up to 5 industries from FIXED_INDUSTRY_LIST using MySQL cache + Gemini (temperature=0, JSON)."""
    if not company_name or not company_name.strip():
        raise HTTPException(status_code=400, detail="Company name required")

    norm_name = normalize_company_name(company_name)
    company_hash = hashlib.sha256(norm_name.encode("utf-8")).hexdigest()

    # 1. Check MySQL company_industry_cache first
    db = SessionLocal()
    try:
        cached_row = db.query(models.CompanyIndustryCache).filter(
            models.CompanyIndustryCache.company_hash == company_hash
        ).first()
        if cached_row is not None:
            saved_list = cached_row.suggested_industries if isinstance(cached_row.suggested_industries, list) else []
            canonical_map = {item.lower(): item for item in FIXED_INDUSTRY_LIST}
            filtered_saved = [canonical_map[x.lower()] for x in saved_list if isinstance(x, str) and x.lower() in canonical_map][:5]
            cache_msg = (
                f"[SUGGEST-INDUSTRY] Cache HIT for company='{norm_name}' "
                f"(hash={company_hash[:12]}...) -> returning cached result with 0 Gemini calls: {filtered_saved}"
            )
            logger.info(cache_msg)
            return {
                "company_name": company_name.strip(),
                "normalized_name": norm_name,
                "company_hash": company_hash,
                "suggested_industries": filtered_saved,
                "available_industries": FIXED_INDUSTRY_LIST,
                "none_matched": len(filtered_saved) == 0,
                "cached": True,
                "gemini_failed": False,
                "model_used": None
            }
    finally:
        db.close()

    # 2. Not cached -> call Gemini with temperature=0 and JSON output
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    call_log = (
        f"[SUGGEST-INDUSTRY] Cache MISS for company='{norm_name}' (hash={company_hash[:12]}...). "
        f"Calling Gemini model='{model_name}' (temperature=0, response_mime_type='application/json')"
    )
    logger.info(call_log)

    try:
        from google import genai
        from google.genai import types
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        client = genai.Client(api_key=gemini_key)
    except Exception as init_err:
        err_msg = f"Gemini initialization failed (model={model_name}): {str(init_err)}"
        logger.error(f"[SUGGEST-INDUSTRY] {err_msg}")
        return {
            "company_name": company_name.strip(),
            "normalized_name": norm_name,
            "company_hash": company_hash,
            "suggested_industries": [],
            "available_industries": FIXED_INDUSTRY_LIST,
            "cached": False,
            "gemini_failed": True,
            "model_used": model_name,
            "message": "Automatic AI industry suggestion is unavailable right now. Please select up to 5 industries manually from the list below."
        }

    fixed_list_json = json.dumps(FIXED_INDUSTRY_LIST, ensure_ascii=False)
    prompt = (
        f"Identify the primary industry categories for the company \"{company_name.strip()}\".\n"
        f"You must choose up to 5 categories strictly from this fixed list of WPI Major Categories:\n"
        f"{fixed_list_json}\n\n"
        "Instructions:\n"
        "1. Select 1 to 5 exact strings from the fixed list above that best describe the company's primary activities.\n"
        "2. If none of the categories on the list apply, answer \"none\".\n"
        "3. Return ONLY a JSON object with a single key `suggested_industries` whose value is either an array of up to 5 exact strings from the list, or the string \"none\"."
    )

    start_time = time.time()
    try:
        config = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json"
        )
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config
        )
        duration = time.time() - start_time

        raw_text = getattr(response, "text", None)
        if not raw_text:
            try:
                raw_text = response.candidates[0].content.parts[0].text
            except Exception:
                raw_text = None
        result_text = (raw_text or "").strip()

        if not result_text:
            raise ValueError("Gemini returned an empty response")

        cleaned_text = result_text
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        match = _re.search(r"\{[\s\S]*\}", cleaned_text)
        parsed_text = match.group(0) if match else cleaned_text
        data = json.loads(parsed_text)

        raw_suggested = data.get("suggested_industries", [])
        canonical_map = {item.lower(): item for item in FIXED_INDUSTRY_LIST}
        valid_industries = []
        discarded_items = []

        if isinstance(raw_suggested, str):
            if raw_suggested.strip().lower() != "none" and raw_suggested.strip().lower() in canonical_map:
                valid_industries.append(canonical_map[raw_suggested.strip().lower()])
            elif raw_suggested.strip().lower() != "none":
                discarded_items.append(raw_suggested)
        elif isinstance(raw_suggested, list):
            for item in raw_suggested:
                if not isinstance(item, str):
                    continue
                cleaned_item = item.strip()
                if not cleaned_item or cleaned_item.lower() == "none":
                    continue
                # Strip optional "(A)." prefix if Gemini ever includes it
                cleaned_no_prefix = _re.sub(r"^\([A-Z]\)\.\s*", "", cleaned_item).strip()
                if cleaned_item.lower() in canonical_map:
                    canon = canonical_map[cleaned_item.lower()]
                elif cleaned_no_prefix.lower() in canonical_map:
                    canon = canonical_map[cleaned_no_prefix.lower()]
                else:
                    discarded_items.append(cleaned_item)
                    continue
                if canon not in valid_industries:
                    valid_industries.append(canon)
                if len(valid_industries) >= 5:
                    break

        success_msg = (
            f"[SUGGEST-INDUSTRY] Gemini call SUCCESS in {duration:.2f}s using model='{model_name}' "
            f"for company='{norm_name}' -> matched={valid_industries} (discarded={discarded_items})"
        )
        logger.info(success_msg)

        # Save in MySQL company_industry_cache
        db = SessionLocal()
        try:
            existing = db.query(models.CompanyIndustryCache).filter(
                models.CompanyIndustryCache.company_hash == company_hash
            ).first()
            if not existing:
                cache_entry = models.CompanyIndustryCache(
                    company_hash=company_hash,
                    normalized_name=norm_name,
                    suggested_industries=valid_industries
                )
                db.add(cache_entry)
                db.commit()
        except Exception as db_err:
            db.rollback()
            logger.warning(f"Failed to write to company_industry_cache: {db_err}")
        finally:
            db.close()

        none_matched = len(valid_industries) == 0
        return {
            "company_name": company_name.strip(),
            "normalized_name": norm_name,
            "company_hash": company_hash,
            "suggested_industries": valid_industries,
            "available_industries": FIXED_INDUSTRY_LIST,
            "none_matched": none_matched,
            "cached": False,
            "gemini_failed": False,
            "model_used": model_name,
            "message": (
                "No matching industry was found automatically for this company. Please select manually from the list below."
                if none_matched else None
            )
        }

    except Exception as e:
        duration = time.time() - start_time
        fail_msg = (
            f"[SUGGEST-INDUSTRY] Gemini call FAILED in {duration:.2f}s using model='{model_name}' "
            f"for company='{norm_name}': {type(e).__name__}: {str(e)}"
        )
        logger.error(fail_msg)
        return {
            "company_name": company_name.strip(),
            "normalized_name": norm_name,
            "company_hash": company_hash,
            "suggested_industries": [],
            "available_industries": FIXED_INDUSTRY_LIST,
            "none_matched": False,
            "cached": False,
            "gemini_failed": True,
            "model_used": model_name,
            "message": "AI industry suggestion could not be completed. Please pick your company's industry manually from the fixed WPI Major Category list below."
        }


# ==============================================================================
# COLUMN ANALYSIS, VALIDATION, MAPPING PERSISTENCE & SAMPLE TEMPLATE
# ==============================================================================
from typing import Optional, Dict, List, Any
from fastapi import Request
from fastapi.responses import StreamingResponse
import io

FIELD_METADATA = [
    {"field": "asset_description", "label": "Asset Description", "requirement": "required"},
    {"field": "capitalized_date", "label": "Capitalized Date / Purchase Year", "requirement": "required"},
    {"field": "acquisition_value", "label": "Acquisition Value (Original Cost)", "requirement": "required"},
    {"field": "major_category", "label": "Category (Major Category / Asset Group)", "requirement": "recommended"},
    {"field": "sub_category", "label": "Second Category Column (Sub-Category / Class)", "requirement": "optional"},
    {"field": "asset_code", "label": "Asset Code / ID", "requirement": "optional"},
    {"field": "location", "label": "Location / Plant", "requirement": "optional"},
    {"field": "accumulated_depreciation", "label": "Accumulated Depreciation", "requirement": "optional"},
    {"field": "book_value", "label": "Net Book Value", "requirement": "optional"},
]

def _get_optional_user(request: Optional[Request]):
    if not request:
        return None
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        return None
    db = SessionLocal()
    try:
        import auth as _auth
        payload = _auth.decode_access_token(token)
        if not payload:
            return None
        uid = payload.get("sub")
        if not uid:
            return None
        user = db.query(models.User).filter(models.User.id == int(uid)).first()
        return user
    except Exception:
        return None
    finally:
        db.close()

def _clean_cell_display(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", "nat"):
        return ""
    if s.endswith(" 00:00:00"):
        s = s[:-9]
    return s

def _compute_headers_hash(headers: List[str]) -> str:
    from column_mapper import normalize_header
    norm_parts = [normalize_header(h) for h in headers if str(h).strip() != ""]
    return hashlib.sha256("|".join(norm_parts).encode("utf-8")).hexdigest()

def _build_field_summary(
    field_meta: dict,
    detected_col: Optional[str],
    confidence: str,
    method: str,
    column_samples: Dict[str, List[str]],
    column_validations: Dict[str, Dict[str, dict]]
) -> dict:
    field = field_meta["field"]
    label = field_meta["label"]
    req_type = field_meta["requirement"]

    if detected_col == "__NO_CATEGORY__" and field == "major_category":
        return {
            "field": field,
            "label": label,
            "requirement": req_type,
            "detected_column": "__NO_CATEGORY__",
            "mapped_column": "__NO_CATEGORY__",
            "confidence": "HIGH",
            "method": method or "USER_CHOICE",
            "sample_values": [],
            "status": "Found",
            "validation": {"valid": True, "warning": None},
            "message": "No category column selected — assets will be classified from their description."
        }

    if detected_col and detected_col in column_samples:
        samples = column_samples.get(detected_col, [])[:5]
        val_info = column_validations.get(detected_col, {}).get(field, {"valid": True, "warning": None})
        if not val_info.get("valid", True):
            status_str = "Please check"
            msg = val_info.get("warning") or f"Please verify that '{detected_col}' is the right column for {label}."
        elif confidence == "HIGH":
            status_str = "Found"
            msg = f"Matched to '{detected_col}'."
        else:
            status_str = "Please check"
            msg = f"We matched '{detected_col}' with {confidence.lower()} confidence. Please check the sample values to make sure it is right."
        return {
            "field": field,
            "label": label,
            "requirement": req_type,
            "detected_column": detected_col,
            "mapped_column": detected_col,
            "confidence": confidence,
            "method": method,
            "sample_values": samples,
            "status": status_str,
            "validation": val_info,
            "message": msg
        }

    # Not found
    if field == "asset_description":
        msg = "We couldn’t find an Asset Description column. Please pick the column that describes each asset."
    elif field == "capitalized_date":
        msg = "We couldn’t find a Date or Year column. Please pick the column with the purchase or capitalization date/year."
    elif field == "acquisition_value":
        msg = "We couldn’t find an Acquisition Value (Cost) column. Please pick the column containing the original purchase cost."
    elif field == "major_category":
        msg = "We couldn’t find a Category column. Pick it from the list, or choose ‘No category column’."
    else:
        msg = "Optional column — not detected in this file."

    return {
        "field": field,
        "label": label,
        "requirement": req_type,
        "detected_column": None,
        "mapped_column": None,
        "confidence": "NONE",
        "method": "NONE",
        "sample_values": [],
        "status": "Not found",
        "validation": {"valid": req_type == "optional", "warning": None},
        "message": msg
    }

@app.post("/analyze-columns")
async def analyze_columns(
    request: Request,
    file: UploadFile = File(...),
    header_row_index: Optional[int] = Form(None),
    sheet_name: Optional[str] = Form(None)
):
    import pandas as pd
    from column_mapper import resolve_columns, validate_column_choice, CANONICAL_FIELDS, normalize_header
    
    current_user = _get_optional_user(request)
    client_ip = request.client.host if request and request.client else "unknown"
    temp_path = os.path.join(BASE_DIR, f"temp_{uuid.uuid4().hex}_{file.filename}")
    try:
        await save_upload_file_safe(file, temp_path, MAX_UPLOAD_MB)
    except HTTPException as upload_exc:
        db_u = SessionLocal()
        try:
            record_audit_event(
                db_u,
                actor_id=current_user.id if current_user else None,
                action="UPLOAD_FAILED",
                target=f"file:{file.filename}",
                user_email=current_user.email if current_user else None,
                file_name=file.filename,
                status="FAILED",
                details=f"File upload failed: {upload_exc.detail}",
                ip_address=client_ip
            )
        finally:
            db_u.close()
        raise upload_exc

    try:
        xl = pd.ExcelFile(temp_path)
        best_sheet = xl.sheet_names[0]
        if sheet_name and sheet_name in xl.sheet_names:
            best_sheet = sheet_name
        else:
            max_rows = -1
            for s_name in xl.sheet_names:
                try:
                    df_sheet = xl.parse(s_name, nrows=1000)
                    if len(df_sheet) > max_rows:
                        max_rows = len(df_sheet)
                        best_sheet = s_name
                except Exception:
                    pass

        df_head = xl.parse(best_sheet, header=None, nrows=35)
        all_known_aliases = set()
        for aliases in CANONICAL_FIELDS.values():
            all_known_aliases.update(aliases)

        auto_header_idx = 0
        max_score = (-1, -1)
        for i in range(len(df_head)):
            row = df_head.iloc[i].fillna("").astype(str).tolist()
            non_digit_cells = sum(
                1 for cell in row
                if cell.strip() != "" and not cell.strip().replace(".", "", 1).replace("-", "", 1).isdigit()
            )
            alias_hits = sum(1 for cell in row if normalize_header(cell) in all_known_aliases)
            score_tuple = (alias_hits, non_digit_cells)
            if score_tuple > max_score and non_digit_cells > 0:
                max_score = score_tuple
                auto_header_idx = i

        if header_row_index is not None:
            best_header_idx = max(0, min(int(header_row_index), max(0, len(df_head) - 1)))
        else:
            best_header_idx = auto_header_idx

        headers = df_head.iloc[best_header_idx].fillna("").astype(str).tolist()
        available_columns = [h for h in headers if str(h).strip() != ""]

        # Read up to 25 data rows immediately following best_header_idx (header=None so first data row is preserved!)
        raw_data_df = xl.parse(best_sheet, header=None, skiprows=best_header_idx + 1, nrows=25)
        all_sample_rows = [
            [_clean_cell_display(v) for v in row.tolist()]
            for _, row in raw_data_df.iterrows()
        ]
        # Filter out completely empty rows
        all_sample_rows = [r for r in all_sample_rows if any(c != "" for c in r)]
        preview_rows = all_sample_rows[:5]

        # Count total data rows read in best_sheet
        try:
            total_rows_df = xl.parse(best_sheet, header=None, skiprows=best_header_idx + 1, usecols=[0])
            total_rows = int(len(total_rows_df.dropna(how="all")))
        except Exception:
            total_rows = len(all_sample_rows)

        detection_results = resolve_columns(headers, all_sample_rows)
        suggestions = detection_results.get("suggestions", {})

        # If a second category column (asset_class or sub_category) was detected that is DIFFERENT from major_category,
        # expose it under sub_category so the optional second category dropdown shows it cleanly.
        major_col = suggestions.get("major_category", {}).get("mapped_column")
        sub_col = suggestions.get("sub_category", {}).get("mapped_column")
        class_col = suggestions.get("asset_class", {}).get("mapped_column")
        if sub_col == major_col:
            if class_col and class_col != major_col:
                suggestions["sub_category"] = dict(suggestions["asset_class"])
            else:
                suggestions["sub_category"] = {"mapped_column": None, "confidence": "NONE", "method": "NONE", "score": 0.0}
        elif not sub_col and class_col and class_col != major_col:
            suggestions["sub_category"] = dict(suggestions["asset_class"])

        # Build per-column 3-5 sample values and content validations
        column_samples: Dict[str, List[str]] = {}
        column_validations: Dict[str, Dict[str, dict]] = {}
        for col_idx, col_name in enumerate(headers):
            if str(col_name).strip() == "":
                continue
            col_vals = [
                row[col_idx] for row in all_sample_rows
                if col_idx < len(row) and str(row[col_idx]).strip() != ""
            ]
            column_samples[col_name] = col_vals[:5]
            column_validations[col_name] = {
                f_key: validate_column_choice(f_key, col_vals, col_name)
                for f_key in ["asset_description", "capitalized_date", "acquisition_value", "major_category", "sub_category"]
            }

        # Check saved user mapping for this file type (headers_hash)
        headers_hash = _compute_headers_hash(headers)
        saved_user_mapping = None
        current_user = _get_optional_user(request)
        db = SessionLocal()
        try:
            q = db.query(models.UserColumnMapping).filter(
                models.UserColumnMapping.headers_hash == headers_hash
            )
            if current_user is not None:
                user_specific = q.filter(models.UserColumnMapping.user_id == current_user.id).order_by(models.UserColumnMapping.updated_at.desc()).first()
                saved_row = user_specific or q.order_by(models.UserColumnMapping.updated_at.desc()).first()
            else:
                saved_row = q.order_by(models.UserColumnMapping.updated_at.desc()).first()

            if saved_row and isinstance(saved_row.mapping_json, dict):
                saved_user_mapping = saved_row.mapping_json
                for f_key, saved_col in saved_user_mapping.items():
                    if saved_col == "__NO_CATEGORY__" and f_key == "major_category":
                        suggestions["major_category"] = {
                            "mapped_column": "__NO_CATEGORY__",
                            "confidence": "HIGH",
                            "method": "USER_SAVED",
                            "score": 1.0
                        }
                    elif saved_col and saved_col in column_samples:
                        val_check = column_validations.get(saved_col, {}).get(f_key, {"valid": True})
                        if val_check.get("valid", True):
                            suggestions[f_key] = {
                                "mapped_column": saved_col,
                                "confidence": "HIGH",
                                "method": "USER_SAVED",
                                "score": 1.0
                            }
        except Exception as db_err:
            logger.warning(f"Could not read user_column_mappings: {db_err}")
        finally:
            db.close()

        # Build field summaries for the table
        field_summaries = []
        for f_meta in FIELD_METADATA:
            f_key = f_meta["field"]
            s_info = suggestions.get(f_key, {})
            field_summaries.append(
                _build_field_summary(
                    f_meta,
                    s_info.get("mapped_column"),
                    s_info.get("confidence", "NONE"),
                    s_info.get("method", "NONE"),
                    column_samples,
                    column_validations
                )
            )

        summary_by_field = {item["field"]: item for item in field_summaries}

        # Determine should_skip_review:
        # Show "Check your columns" automatically ONLY when:
        # - Any of the 3 required fields (asset_description, capitalized_date, acquisition_value) is not Found or invalid
        # - Category (major_category) is not Found (so user sees the prompt to pick Category or 'No category column')
        # - Any detected field has low/medium confidence (status == 'Please check')
        required_ok = all(
            summary_by_field[rk]["status"] == "Found" and summary_by_field[rk]["validation"].get("valid", False)
            for rk in ("asset_description", "capitalized_date", "acquisition_value")
        )
        category_ok = summary_by_field["major_category"]["status"] == "Found"
        any_please_check = any(item["status"] == "Please check" for item in field_summaries)

        should_skip_review = bool(required_ok and category_ok and not any_please_check)

        # Also return first 8 raw rows of the sheet so the user can see what is in Row 1, Row 2, Row 3...
        sheet_top_rows = [
            [_clean_cell_display(v) for v in df_head.iloc[r_idx].tolist()]
            for r_idx in range(min(10, len(df_head)))
        ]

        return {
            "success": True,
            "header_row_index": best_header_idx,
            "header_row_number": best_header_idx + 1,
            "auto_detected_header_row_index": auto_header_idx,
            "max_header_row_options": min(20, max(5, len(df_head))),
            "sheet_name": best_sheet,
            "sheet_names": xl.sheet_names,
            "headers": headers,
            "available_columns": available_columns,
            "headers_hash": headers_hash,
            "detection": detection_results,
            "field_summaries": field_summaries,
            "column_samples": column_samples,
            "column_validations": column_validations,
            "sample_data": preview_rows,
            "sheet_top_rows": sheet_top_rows,
            "should_skip_review": should_skip_review,
            "saved_user_mapping": saved_user_mapping,
            "total_rows": total_rows
        }
    except Exception as e:
        logger.exception(f"Error analyzing columns for file '{file.filename}': {e}")
        db_u = SessionLocal()
        try:
            record_audit_event(
                db_u,
                actor_id=current_user.id if current_user else None,
                action="UPLOAD_FAILED",
                target=f"file:{file.filename}",
                user_email=current_user.email if current_user else None,
                file_name=file.filename,
                status="FAILED",
                details=f"Excel file parsing/column analysis failed: {str(e)}",
                ip_address=client_ip
            )
        finally:
            db_u.close()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'xl' in locals() and hasattr(xl, 'close'):
            xl.close()
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ==============================================================================
# LONG JOBS: ASYNC CALCULATION WITH PROGRESS ENDPOINT
# ==============================================================================
@app.post("/calculate-job")
async def calculate_file_job(
    request: Request,
    file: UploadFile = File(...), 
    wpiGroup: str = Form(...),
    userMapping: str = Form("{}"),
    headerRowIndex: int = Form(0),
    sheetName: str = Form(""),
    companyName: str = Form(""),
    industry: str = Form(""),
    recalculate: bool = Form(False),
    current_user: models.User = Depends(get_current_active_user)
):
    """Initiates an asynchronous background calculation job linked to the authenticated user."""
    client_ip = request.client.host if request and request.client else "unknown"
    try:
        content = await read_upload_file_safe(file, MAX_UPLOAD_MB)
    except HTTPException as upload_exc:
        db_err = SessionLocal()
        try:
            record_audit_event(
                db_err,
                actor_id=current_user.id,
                action="UPLOAD_FAILED",
                target=f"file:{file.filename}",
                user_email=current_user.email,
                file_name=file.filename,
                status="FAILED",
                details=f"Upload rejected in /calculate-job: {upload_exc.detail}",
                ip_address=client_ip
            )
        finally:
            db_err.close()
        raise upload_exc

    file_sha256 = hashlib.sha256(content).hexdigest()
    master_version = get_master_version_hash()

    # Same file shortcut check
    db = SessionLocal()
    try:
        if not recalculate:
            existing = db.query(models.Analysis).filter(
                models.Analysis.user_id == current_user.id,
                models.Analysis.file_sha256 == file_sha256,
                models.Analysis.master_version == master_version,
                models.Analysis.status == "completed"
            ).order_by(models.Analysis.created_at.desc()).first()

            if existing:
                return {
                    "duplicate_found": True,
                    "analysis_id": existing.id,
                    "company_name": existing.company_name or "",
                    "original_filename": existing.original_filename,
                    "created_at": existing.created_at.isoformat() if existing.created_at else None,
                    "master_version": existing.master_version[:8] if existing.master_version else "",
                    "rows_total": existing.rows_total or 0,
                    "total_acquisition": float(existing.total_acquisition or 0),
                    "total_replacement": float(existing.total_replacement or 0)
                }

        # Create new Analysis in processing status
        new_analysis = models.Analysis(
            user_id=current_user.id,
            company_name=companyName or file.filename.rsplit(".", 1)[0],
            industry=industry or wpiGroup,
            original_filename=file.filename,
            file_sha256=file_sha256,
            master_version=master_version,
            status="processing"
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        analysis_id = new_analysis.id
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="FILE_UPLOAD",
            target=f"file:{file.filename}",
            user_email=current_user.email,
            file_name=file.filename,
            status="SUCCESS",
            details=f"Excel file '{file.filename}' uploaded for analysis #{analysis_id}",
            ip_address=client_ip
        )
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="ANALYSIS_STARTED",
            target=f"analysis:{analysis_id}:{file.filename}",
            user_email=current_user.email,
            file_name=file.filename,
            status="SUCCESS",
            details=f"Started FAR analysis #{analysis_id} on '{file.filename}' (WPI group: {wpiGroup})",
            ip_address=client_ip
        )
    finally:
        db.close()

    job_id = uuid.uuid4().hex
    temp_path = os.path.join(BASE_DIR, f"temp_job_{job_id}_{file.filename}")
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        user_mapping_dict = json.loads(userMapping)
    except Exception:
        user_mapping_dict = {}

    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "analysis_id": analysis_id,
            "status": "pending",
            "progress": 0,
            "message": "Job queued for processing...",
            "result": None,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time()
        }

    # Spawn background worker thread
    thread = threading.Thread(
        target=calculation_worker,
        args=(job_id, temp_path, wpiGroup, user_mapping_dict, headerRowIndex, sheetName, analysis_id),
        daemon=True
    )
    thread.start()

    return {"job_id": job_id, "analysis_id": analysis_id, "status": "pending"}

@app.get("/calculate-job/{job_id}")
async def get_calculate_job_status(job_id: str):
    """Poll calculation job status and progress (0-100%)."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job ID not found")
        return {
            "job_id": job["job_id"],
            "analysis_id": job.get("analysis_id"),
            "status": job["status"],
            "progress": job["progress"],
            "message": job["message"],
            "result": job["result"],
            "error": job["error"]
        }

# ==============================================================================
# SYNCHRONOUS CALCULATION (Legacy / Direct)
# ==============================================================================
@app.post("/calculate")
async def calculate_file(
    request: Request,
    file: UploadFile = File(...), 
    wpiGroup: str = Form(...),
    userMapping: str = Form("{}"),
    headerRowIndex: int = Form(0),
    sheetName: str = Form(""),
    companyName: str = Form(""),
    industry: str = Form(""),
    recalculate: bool = Form(False),
    current_user: models.User = Depends(get_current_active_user)
):
    """Synchronous calculation linked to authenticated user with database persistence."""
    client_ip = request.client.host if request and request.client else "unknown"
    try:
        content = await read_upload_file_safe(file, MAX_UPLOAD_MB)
    except HTTPException as upload_exc:
        db_err = SessionLocal()
        try:
            record_audit_event(
                db_err,
                actor_id=current_user.id,
                action="UPLOAD_FAILED",
                target=f"file:{file.filename}",
                user_email=current_user.email,
                file_name=file.filename,
                status="FAILED",
                details=f"Upload rejected in /calculate: {upload_exc.detail}",
                ip_address=client_ip
            )
        finally:
            db_err.close()
        raise upload_exc

    file_sha256 = hashlib.sha256(content).hexdigest()
    master_version = get_master_version_hash()

    db = SessionLocal()
    try:
        if not recalculate:
            existing = db.query(models.Analysis).filter(
                models.Analysis.user_id == current_user.id,
                models.Analysis.file_sha256 == file_sha256,
                models.Analysis.master_version == master_version,
                models.Analysis.status == "completed"
            ).order_by(models.Analysis.created_at.desc()).first()

            if existing:
                return {
                    "duplicate_found": True,
                    "analysis_id": existing.id,
                    "company_name": existing.company_name or "",
                    "original_filename": existing.original_filename,
                    "created_at": existing.created_at.isoformat() if existing.created_at else None,
                    "master_version": existing.master_version[:8] if existing.master_version else "",
                    "rows_total": existing.rows_total or 0,
                    "total_acquisition": float(existing.total_acquisition or 0),
                    "total_replacement": float(existing.total_replacement or 0)
                }

        new_analysis = models.Analysis(
            user_id=current_user.id,
            company_name=companyName or file.filename.rsplit(".", 1)[0],
            industry=industry or wpiGroup,
            original_filename=file.filename,
            file_sha256=file_sha256,
            master_version=master_version,
            status="processing"
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        analysis_id = new_analysis.id
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="FILE_UPLOAD",
            target=f"file:{file.filename}",
            user_email=current_user.email,
            file_name=file.filename,
            status="SUCCESS",
            details=f"Excel file '{file.filename}' uploaded for analysis #{analysis_id}",
            ip_address=client_ip
        )
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="ANALYSIS_STARTED",
            target=f"analysis:{analysis_id}:{file.filename}",
            user_email=current_user.email,
            file_name=file.filename,
            status="SUCCESS",
            details=f"Started FAR analysis #{analysis_id} on '{file.filename}' (WPI group: {wpiGroup})",
            ip_address=client_ip
        )
    finally:
        db.close()

    temp_path = os.path.join(BASE_DIR, f"temp_sync_{uuid.uuid4().hex}_{file.filename}")
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        user_mapping_dict = json.loads(userMapping)
        result = process_file(temp_path, wpiGroup, user_mapping_dict, headerRowIndex, sheetName)

        # Persist rows to DB
        db = SessionLocal()
        try:
            analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
            if analysis:
                metrics = result.get("metrics", {})
                mapped_data = result.get("mappedData", [])
                headers = result.get("headers", [])

                analysis.columns_order = headers
                analysis.rows_total = metrics.get("Total Assets", len(mapped_data))
                analysis.rows_calculated = metrics.get("Calculated Assets", 0)
                analysis.rows_manual_review = metrics.get("Manual Review Count", 0)
                analysis.rows_not_applicable = metrics.get("Not Applicable Count", 0)
                analysis.total_acquisition = metrics.get("Total Acquisition Value", 0.0)
                analysis.total_replacement = metrics.get("Total Replacement Value", 0.0)
                analysis.gemini_calls = metrics.get("gemini_calls", 0)

                BATCH_SIZE = 1000
                for i in range(0, len(mapped_data), BATCH_SIZE):
                    chunk = mapped_data[i:i + BATCH_SIZE]
                    row_models = []
                    for idx_in_chunk, r in enumerate(chunk):
                        row_no = i + idx_in_chunk + 1
                        acq_val = r.get("acquisitionValue")
                        diff_val = r.get("difference")
                        inc_pct = None
                        if acq_val and diff_val is not None:
                            try:
                                inc_pct = float(diff_val) / float(acq_val)
                            except Exception:
                                inc_pct = 0.0
                        elif r.get("status") in ["Success", "Not Applicable"]:
                            inc_pct = 0.0

                        row_models.append(
                            models.AnalysisRow(
                                analysis_id=analysis_id,
                                row_no=row_no,
                                asset_code=str(r.get("assetCode") or "") if r.get("assetCode") is not None else None,
                                description=str(r.get("description") or "") if r.get("description") is not None else None,
                                capitalized_date=str(r.get("capDate") or "") if r.get("capDate") is not None else None,
                                purchase_year=r.get("purchaseYear") if isinstance(r.get("purchaseYear"), int) else None,
                                acquisition_value=acq_val if isinstance(acq_val, (int, float)) else None,
                                accumulated_dep=r.get("accumDep") if isinstance(r.get("accumDep"), (int, float)) else None,
                                book_value=r.get("bookValue") if isinstance(r.get("bookValue"), (int, float)) else None,
                                major_category=str(r.get("majorCategory") or "") if r.get("majorCategory") is not None else None,
                                sub_category=str(r.get("subCategory") or "") if r.get("subCategory") is not None else None,
                                asset_class=str(r.get("assetClass") or "") if r.get("assetClass") is not None else None,
                                location=str(r.get("location") or "") if r.get("location") is not None else None,
                                wpi_group=str(r.get("wpiGroup") or "") if r.get("wpiGroup") is not None else None,
                                wpi_series="SERIES_2011-12" if r.get("calculationMethod") == "WPI Based" else None,
                                purchase_wpi=r.get("purchaseWpi") if isinstance(r.get("purchaseWpi"), (int, float)) else None,
                                current_wpi=r.get("currentWpi") if isinstance(r.get("currentWpi"), (int, float)) else None,
                                calculation_method=str(r.get("calculationMethod") or "") if r.get("calculationMethod") is not None else None,
                                status=str(r.get("status") or "") if r.get("status") is not None else None,
                                note=str(r.get("note") or "") if r.get("note") is not None else None,
                                replacement_value=r.get("replacementValue") if isinstance(r.get("replacementValue"), (int, float)) else None,
                                difference=diff_val if isinstance(diff_val, (int, float)) else None,
                                increase_pct=inc_pct,
                                original_row=extract_original_row_dict(r.get("rawRow"), headers)
                            )
                        )
                    db.bulk_save_objects(row_models)
                    db.commit()

                analysis.status = "completed"
                analysis.completed_at = datetime.datetime.utcnow()
                db.commit()
                record_audit_event(
                    db,
                    actor_id=analysis.user_id,
                    action="ANALYSIS_COMPLETED",
                    target=f"analysis:{analysis.id}:{analysis.original_filename}",
                    user_email=current_user.email,
                    file_name=analysis.original_filename,
                    status="SUCCESS",
                    details=f"Analysis #{analysis.id} completed ({analysis.rows_calculated}/{analysis.rows_total} rows calculated)",
                    ip_address=client_ip
                )

                result["analysis_id"] = analysis_id
                result["metrics"]["downloadUrl"] = f"/analyses/{analysis_id}/download"
        except Exception as save_err:
            logger.exception(f"Failed to persist rows in sync calculate: {save_err}")
            db.rollback()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = f"Failed to save result rows: {str(save_err)}"
                db.commit()
                record_audit_event(
                    db,
                    actor_id=analysis.user_id,
                    action="ANALYSIS_FAILED",
                    target=f"analysis:{analysis.id}:{analysis.original_filename}",
                    user_email=current_user.email,
                    file_name=analysis.original_filename,
                    status="FAILED",
                    details=f"Failed to save result rows for analysis #{analysis.id}: {str(save_err)}",
                    ip_address=client_ip
                )
            raise save_err
        finally:
            db.close()

        return Response(content=json.dumps(result), media_type="application/json")
    except Exception as e:
        logger.exception(f"Error in synchronous calculate: {e}")
        db_err = SessionLocal()
        try:
            failed_analysis = db_err.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
            if failed_analysis and failed_analysis.status != "failed":
                failed_analysis.status = "failed"
                failed_analysis.error_message = str(e)
                db_err.commit()
                record_audit_event(
                    db_err,
                    actor_id=failed_analysis.user_id,
                    action="ANALYSIS_FAILED",
                    target=f"analysis:{failed_analysis.id}:{failed_analysis.original_filename}",
                    user_email=current_user.email,
                    file_name=failed_analysis.original_filename,
                    status="FAILED",
                    details=f"Analysis #{failed_analysis.id} calculation failed: {str(e)}",
                    ip_address=client_ip
                )
        finally:
            db_err.close()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        # Clean stray excel files to satisfy Ground Rule 2
        for f in os.listdir(DOWNLOADS_DIR):
            if f.endswith(".xlsx"):
                try:
                    os.remove(os.path.join(DOWNLOADS_DIR, f))
                except Exception:
                    pass
        if os.path.exists("WPI_Validation_Report.xlsx"):
            try:
                os.remove("WPI_Validation_Report.xlsx")
            except Exception:
                pass

# ==============================================================================
# CACHE, FIELD ALIAS VALIDATION & SAMPLE TEMPLATE MANAGEMENT
# ==============================================================================
from column_mapper import (
    CANONICAL_FIELDS,
    DEFAULT_CANONICAL_FIELDS,
    save_alias_cache,
    load_alias_cache,
    normalize_header,
    validate_column_choice,
    generate_validation_summary
)

class ConfirmAliasRequest(BaseModel):
    field: str
    column: str
    sample_values: Optional[List[str]] = None
    require_admin_approval: bool = False

class ConfirmMappingRequest(BaseModel):
    headers: List[str]
    header_row_index: int = 0
    mapping: Dict[str, Optional[str]]
    sample_data: Optional[List[List[Any]]] = None
    require_admin_approval: bool = False

@app.post("/confirm-alias")
async def confirm_alias(req: ConfirmAliasRequest, request: Request):
    field = req.field
    if field == "purchase_date":
        field = "capitalized_date"
    if field not in CANONICAL_FIELDS:
        raise HTTPException(status_code=400, detail="Invalid canonical field")

    norm_col = normalize_header(req.column)
    if not norm_col:
        raise HTTPException(status_code=400, detail="Column name cannot be empty")

    samples = [str(v) for v in (req.sample_values or []) if str(v).strip() != ""]
    if samples:
        val_res = validate_column_choice(field, samples, req.column)
        if not val_res.get("valid", False):
            return {
                "success": False,
                "valid": False,
                "warning": val_res.get("warning"),
                "shared_cache_written": False
            }
        passed_validation = True
    else:
        # Without sample values to validate content, never write directly to active shared cache;
        # queue as pending for admin approval instead.
        passed_validation = False

    current_user = _get_optional_user(request)
    status_val = "approved" if (passed_validation and not req.require_admin_approval) else "pending"
    h_hash = hashlib.sha256(f"{field}:{norm_col}".encode("utf-8")).hexdigest()
    val_summary = generate_validation_summary(field, samples) if passed_validation else "Unvalidated"

    db = SessionLocal()
    try:
        existing = db.query(models.ColumnAliasCache).filter(
            models.ColumnAliasCache.header_hash == h_hash
        ).first()
        if existing:
            existing.original_header = req.column
            existing.normalized_header = norm_col
            existing.canonical_field = field
            existing.validation_summary = val_summary
            existing.sample_values = None
            existing.validation_passed = passed_validation
            if existing.status != "approved":
                existing.status = status_val
        else:
            db.add(
                models.ColumnAliasCache(
                    header_hash=h_hash,
                    original_header=req.column,
                    normalized_header=norm_col,
                    canonical_field=field,
                    status=status_val,
                    validation_summary=val_summary,
                    sample_values=None,
                    validation_passed=passed_validation,
                    submitted_by=current_user.id if current_user else None
                )
            )
        db.commit()
    finally:
        db.close()

    if status_val == "approved" and passed_validation:
        if norm_col not in CANONICAL_FIELDS[field]:
            CANONICAL_FIELDS[field].append(norm_col)
        if field == "major_category" and norm_col not in CANONICAL_FIELDS.get("category", []):
            CANONICAL_FIELDS["category"].append(norm_col)
        save_alias_cache()

    return {
        "success": True,
        "valid": True,
        "status": status_val,
        "shared_cache_written": status_val == "approved" and passed_validation
    }

@app.post("/confirm-mapping")
async def confirm_mapping(req: ConfirmMappingRequest, request: Request):
    """
    Validates the user's chosen column mappings against sample values.
    1. Rejects any invalid choice (e.g. text column picked as cost, non-date picked as date)
       with a plain-language warning and NEVER writes unvalidated choices to the shared cache.
    2. Saves the validated mapping for the user's file type (user_column_mappings).
    3. Adds new validated column aliases to column_alias_cache (either approved after passing
       content validation or pending admin approval).
    """
    headers = req.headers or []
    sample_rows = req.sample_data or []

    # Build column data lookup
    col_data_map: Dict[str, List[str]] = {}
    for idx, h in enumerate(headers):
        if str(h).strip() == "":
            continue
        vals = []
        for r in sample_rows:
            if idx < len(r):
                cleaned = _clean_cell_display(r[idx])
                if cleaned != "":
                    vals.append(cleaned)
        col_data_map[h] = vals

    mapping = dict(req.mapping or {})
    # Normalize purchase_date <-> capitalized_date
    if mapping.get("capitalized_date") and not mapping.get("purchase_date"):
        mapping["purchase_date"] = mapping["capitalized_date"]
    elif mapping.get("purchase_date") and not mapping.get("capitalized_date"):
        mapping["capitalized_date"] = mapping["purchase_date"]

    warnings: Dict[str, str] = {}
    validations: Dict[str, dict] = {}

    required_fields = [
        ("asset_description", "Asset Description"),
        ("capitalized_date", "Capitalized Date / Year"),
        ("acquisition_value", "Acquisition Value (Cost)")
    ]
    for f_key, f_label in required_fields:
        chosen_col = mapping.get(f_key)
        if not chosen_col or str(chosen_col).strip() == "":
            warnings[f_key] = f"Please choose a column for {f_label}."
            validations[f_key] = {"valid": False, "warning": warnings[f_key]}
            continue
        if chosen_col not in col_data_map:
            warnings[f_key] = f"Column '{chosen_col}' was not found in the selected header row."
            validations[f_key] = {"valid": False, "warning": warnings[f_key]}
            continue
        val_res = validate_column_choice(f_key, col_data_map[chosen_col], chosen_col)
        validations[f_key] = val_res
        if not val_res.get("valid", False):
            warnings[f_key] = val_res.get("warning") or f"Invalid column selected for {f_label}."

    # Validate Category (recommended)
    cat_col = mapping.get("major_category")
    if not cat_col or str(cat_col).strip() == "":
        warnings["major_category"] = "We couldn’t find a Category column. Pick it from the list, or choose ‘No category column’."
        validations["major_category"] = {"valid": False, "warning": warnings["major_category"]}
    elif cat_col == "__NO_CATEGORY__":
        validations["major_category"] = {"valid": True, "warning": None}
    elif cat_col in col_data_map:
        val_res = validate_column_choice("major_category", col_data_map[cat_col], cat_col)
        validations["major_category"] = val_res
        if not val_res.get("valid", False):
            warnings["major_category"] = val_res.get("warning")

    # Validate optional second category if chosen
    sub_col = mapping.get("sub_category")
    if sub_col and sub_col in col_data_map:
        val_res = validate_column_choice("sub_category", col_data_map[sub_col], sub_col)
        validations["sub_category"] = val_res
        if not val_res.get("valid", False):
            warnings["sub_category"] = val_res.get("warning")

    if warnings:
        return {
            "success": False,
            "valid": False,
            "warnings": warnings,
            "validations": validations,
            "user_mapping_saved": False,
            "shared_cache_written": False,
            "pending_aliases_created": []
        }

    # All required & chosen fields passed content validation!
    headers_hash = _compute_headers_hash(headers)
    current_user = _get_optional_user(request)
    user_id = current_user.id if current_user else None

    shared_written = []
    pending_created = []

    db = SessionLocal()
    try:
        # 1. Save mapping for this user's file type in user_column_mappings
        q = db.query(models.UserColumnMapping).filter(
            models.UserColumnMapping.headers_hash == headers_hash
        )
        if user_id is not None:
            existing_um = q.filter(models.UserColumnMapping.user_id == user_id).first()
        else:
            existing_um = q.filter(models.UserColumnMapping.user_id.is_(None)).first()

        if existing_um:
            existing_um.header_row_index = req.header_row_index
            existing_um.mapping_json = mapping
            existing_um.sample_headers = [h for h in headers if str(h).strip() != ""]
            existing_um.updated_at = datetime.datetime.utcnow()
        else:
            db.add(
                models.UserColumnMapping(
                    user_id=user_id,
                    headers_hash=headers_hash,
                    header_row_index=req.header_row_index,
                    mapping_json=mapping,
                    sample_headers=[h for h in headers if str(h).strip() != ""]
                )
            )

        # 2. Check new validated aliases for column_alias_cache
        track_fields = [
            "asset_description",
            "capitalized_date",
            "acquisition_value",
            "major_category",
            "sub_category",
            "asset_code",
            "location",
            "accumulated_depreciation",
            "book_value"
        ]
        for f_key in track_fields:
            col_name = mapping.get(f_key)
            if not col_name or col_name == "__NO_CATEGORY__" or col_name not in col_data_map:
                continue
            norm_h = normalize_header(col_name)
            if not norm_h:
                continue
            # Double-check content validation before touching column_alias_cache
            val_check = validate_column_choice(f_key, col_data_map[col_name], col_name)
            if not val_check.get("valid", False):
                continue

            default_list = [normalize_header(a) for a in DEFAULT_CANONICAL_FIELDS.get(f_key, [])]
            if f_key == "major_category":
                default_list += [normalize_header(a) for a in DEFAULT_CANONICAL_FIELDS.get("category", [])]

            if norm_h in default_list:
                continue

            val_summary = generate_validation_summary(f_key, col_data_map[col_name])
            h_hash = hashlib.sha256(f"{f_key}:{norm_h}".encode("utf-8")).hexdigest()
            alias_status = "pending" if req.require_admin_approval else "approved"
            existing_alias = db.query(models.ColumnAliasCache).filter(
                models.ColumnAliasCache.header_hash == h_hash
            ).first()
            if existing_alias:
                existing_alias.original_header = col_name
                existing_alias.validation_summary = val_summary
                existing_alias.sample_values = None
                existing_alias.validation_passed = True
                if existing_alias.status != "approved" and not req.require_admin_approval:
                    existing_alias.status = "approved"
                alias_status = existing_alias.status
            else:
                db.add(
                    models.ColumnAliasCache(
                        header_hash=h_hash,
                        original_header=col_name,
                        normalized_header=norm_h,
                        canonical_field=f_key,
                        status=alias_status,
                        validation_summary=val_summary,
                        sample_values=None,
                        validation_passed=True,
                        submitted_by=user_id
                    )
                )

            if alias_status == "approved":
                if norm_h not in CANONICAL_FIELDS.setdefault(f_key, []):
                    CANONICAL_FIELDS[f_key].append(norm_h)
                if f_key == "major_category" and norm_h not in CANONICAL_FIELDS.setdefault("category", []):
                    CANONICAL_FIELDS["category"].append(norm_h)
                shared_written.append({"field": f_key, "column": col_name, "normalized": norm_h})
            else:
                pending_created.append({"field": f_key, "column": col_name, "normalized": norm_h})

        db.commit()
    finally:
        db.close()

    if shared_written:
        save_alias_cache()

    # Build calculator-ready userMapping dict (supporting both purchase_date and capitalized_date)
    calc_mapping = dict(mapping)
    if calc_mapping.get("major_category") == "__NO_CATEGORY__":
        calc_mapping["major_category"] = ""
    if calc_mapping.get("sub_category") and not calc_mapping.get("asset_class"):
        calc_mapping["asset_class"] = calc_mapping["sub_category"]

    return {
        "success": True,
        "valid": True,
        "warnings": {},
        "validations": validations,
        "user_mapping_saved": True,
        "headers_hash": headers_hash,
        "shared_cache_written": len(shared_written) > 0,
        "shared_aliases": shared_written,
        "pending_aliases_created": pending_created,
        "calculator_mapping": calc_mapping
    }

class SaveCacheRequest(BaseModel):
    description: str
    category: str

@app.post('/save-cache')
async def save_cache(req: SaveCacheRequest):
    if req.category in VALID_WPI_GROUPS:
        CATEGORY_CACHE[req.description.lower().strip()] = req.category
        save_category_cache()
        return {'success': True}
    raise HTTPException(status_code=400, detail='Invalid category')

@app.get('/valid-groups')
def get_valid_groups():
    return {'valid_groups': VALID_WPI_GROUPS}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    # Single worker enforcement as required
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
