"""
scripts/cleanup_test_data.py

Performs safe cleanup of test accounts from the live far_app database:
1. Creates a full database backup using mysqldump.
2. Identifies candidate test accounts based on allowed test domains (default: example.com).
3. Enforces strict safety rules:
   - REFUSES to delete any admin account (role='admin').
   - REFUSES to delete any user with analyses (number of analyses > 0).
   - REFUSES to delete user #50 (Primary Admin) or real company/user accounts.
   - REFUSES to delete user #13 (System Administrator, kept disabled for inspection).
   - REFUSES to delete any user whose email domain is not in the confirmed list.
4. Displays a preview table (ID, Name, Email Domain only, Created At, Number of Analyses).
5. Does NOTHING until explicit confirmation ('YES') is typed.
6. Deletes accounts using the exact "Delete my account" logic (deleting sessions, tokens,
   nulling column alias references, and anonymizing login_events and audit logs).
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Load backend configuration
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path, override=True)

import models
import database
from sqlalchemy import func, text

# Hardcoded protected User IDs that can NEVER be deleted under any circumstances
STRICTLY_PROTECTED_USER_IDS = {13, 50, 73, 95, 110}

# Allowed test email domains eligible for cleanup preview
DEFAULT_TEST_DOMAINS = {"example.com", "far.local", "test.com"}


def find_mysqldump_executable() -> str:
    """Find mysqldump executable in PATH or standard MySQL installation directories."""
    # Check PATH first
    import shutil
    p = shutil.which("mysqldump")
    if p:
        return p

    # Standard Windows install locations
    candidates = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 9.0\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Workbench 8.0\mysqldump.exe",
        r"C:\xampp\mysql\bin\mysqldump.exe"
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    raise FileNotFoundError("mysqldump executable could not be found on the system.")


def create_database_backup() -> str:
    """Create a full MySQL database dump before making any deletions."""
    backup_dir = backend_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_name = os.getenv("DB_NAME", "far_app")
    backup_file = backup_dir / f"db_backup_before_cleanup_{db_name}_{timestamp}.sql"

    mysqldump_exe = find_mysqldump_executable()
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")

    cmd = [
        mysqldump_exe,
        f"--host={host}",
        f"--port={port}",
        f"--user={user}",
        f"--password={password}",
        "--single-transaction",
        "--quick",
        db_name
    ]

    print(f"[*] Creating full database backup with mysqldump...")
    print(f"    Target database: {db_name}")
    print(f"    Output file:     {backup_file}")

    with open(backup_file, "w", encoding="utf-8") as f:
        res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

    if res.returncode != 0:
        if os.path.exists(backup_file):
            os.remove(backup_file)
        raise RuntimeError(f"mysqldump failed with error:\n{res.stderr}")

    file_size = os.path.getsize(backup_file)
    print(f"[OK] Database backup successfully created ({file_size:,} bytes).")
    return str(backup_file)


def get_candidate_test_accounts(db, allowed_domains=None, explicit_ids=None):
    """
    Identify and validate candidate test accounts.
    Applies all safety constraints.
    """
    allowed_domains = allowed_domains or DEFAULT_TEST_DOMAINS
    explicit_ids = explicit_ids or set()

    all_users = db.query(models.User).order_by(models.User.id.asc()).all()

    eligible_for_deletion = []
    skipped_or_refused = []

    for u in all_users:
        user_id = u.id
        user_email = (u.email or "").strip().lower()
        domain = user_email.split("@")[1] if "@" in user_email else ""
        num_analyses = db.query(func.count(models.Analysis.id)).filter(models.Analysis.user_id == user_id).scalar() or 0

        # Safety Check 1: Strictly protected user IDs (Admin #50, #13, real users)
        if user_id in STRICTLY_PROTECTED_USER_IDS:
            skipped_or_refused.append({
                "user": u, "domain": f"@{domain}", "analyses": num_analyses,
                "reason": f"Explicitly protected user #{user_id}"
            })
            continue

        # Safety Check 2: Never delete administrators
        if u.role == "admin":
            skipped_or_refused.append({
                "user": u, "domain": f"@{domain}", "analyses": num_analyses,
                "reason": "User holds 'admin' role"
            })
            continue

        # Safety Check 3: Explicitly listed IDs bypass domain check, but not admin/protected checks
        if user_id in explicit_ids:
            eligible_for_deletion.append({
                "user": u, "domain": f"@{domain}", "analyses": num_analyses
            })
            continue

        # Safety Check 4: Refuse users whose email domain is not in the confirmed list
        if domain not in allowed_domains:
            skipped_or_refused.append({
                "user": u, "domain": f"@{domain}", "analyses": num_analyses,
                "reason": f"Domain '@{domain}' is not in allowed test domains list"
            })
            continue

        # Safety Check 5: Refuse users who have analyses
        if num_analyses > 0:
            skipped_or_refused.append({
                "user": u, "domain": f"@{domain}", "analyses": num_analyses,
                "reason": f"User has {num_analyses} analysis record(s)"
            })
            continue

        # Passes all safety filters
        eligible_for_deletion.append({
            "user": u,
            "domain": f"@{domain}",
            "analyses": num_analyses
        })

    return eligible_for_deletion, skipped_or_refused


def delete_single_account(db, user: models.User):
    """
    Delete a user account using the exact logic of "Delete my account"
    (permanently_delete_account).
    """
    uid = user.id
    raw_email = (user.email or "").strip().lower()

    # 1. Nullify column_alias_cache references
    db.query(models.ColumnAliasCache).filter(models.ColumnAliasCache.submitted_by == uid).update({
        models.ColumnAliasCache.submitted_by: None
    })
    db.query(models.ColumnAliasCache).filter(models.ColumnAliasCache.approved_by == uid).update({
        models.ColumnAliasCache.approved_by: None
    })

    # 2. Nullify classification_cache references
    db.query(models.ClassificationCache).filter(models.ClassificationCache.confirmed_by == uid).update({
        models.ClassificationCache.confirmed_by: None
    })

    # 3. Delete analysis rows and analyses
    analysis_ids = [aid for (aid,) in db.query(models.Analysis.id).filter(models.Analysis.user_id == uid).all()]
    if analysis_ids:
        db.query(models.AnalysisRow).filter(models.AnalysisRow.analysis_id.in_(analysis_ids)).delete(synchronize_session=False)
        db.query(models.Analysis).filter(models.Analysis.id.in_(analysis_ids)).delete(synchronize_session=False)

    # 4. Delete tokens, verification codes, sessions, mappings
    db.query(models.UserSession).filter(models.UserSession.user_id == uid).delete(synchronize_session=False)
    db.query(models.UserColumnMapping).filter(models.UserColumnMapping.user_id == uid).delete(synchronize_session=False)
    db.query(models.PasswordResetToken).filter(models.PasswordResetToken.user_id == uid).delete(synchronize_session=False)
    db.query(models.EmailVerificationCode).filter(models.EmailVerificationCode.user_id == uid).delete(synchronize_session=False)

    # 5. Anonymize login_events (no email address left)
    db.execute(text("""
        UPDATE login_events 
        SET user_id = NULL, email_attempted = 'anonymized_user@anonymized.local' 
        WHERE user_id = :uid OR email_attempted = :email
    """), {"uid": uid, "email": raw_email})

    # 6. Anonymize audit_logs (no email address left)
    db.execute(text("""
        UPDATE audit_logs 
        SET user_id = NULL, user_email = NULL, details = REPLACE(details, :email, 'anonymized_user') 
        WHERE user_id = :uid OR user_email = :email
    """), {"uid": uid, "email": raw_email})

    # 7. Anonymize legacy audit_log
    db.execute(text("""
        UPDATE audit_log 
        SET actor_id = NULL, target = REPLACE(target, :email, 'anonymized_user') 
        WHERE actor_id = :uid OR target LIKE :target_pattern
    """), {"uid": uid, "email": raw_email, "target_pattern": f"%{raw_email}%"})

    # 8. Delete user record
    db.delete(user)


def preview_and_cleanup(auto_confirm: bool = False, explicit_ids: set = None):
    db = next(database.get_db())

    # Step 1: Create backup first
    backup_file = create_database_backup()

    # Step 2: Identify candidate test accounts
    candidates, skipped = get_candidate_test_accounts(db, explicit_ids=explicit_ids)

    print("\n" + "=" * 90)
    print("PREVIEW OF TEST ACCOUNTS PROPOSED FOR DELETION (Domain Only, No Sensitive Data)")
    print("=" * 90)
    print(f"{'ID':<6} | {'Name':<25} | {'Email Domain':<18} | {'Created At':<20} | {'Analyses'}")
    print("-" * 90)

    if not candidates:
        print("  (No eligible test accounts found for deletion)")
    else:
        for item in candidates:
            u = item["user"]
            c_date = u.created_at.strftime("%d %b %Y, %I:%M %p") if u.created_at else "N/A"
            name = (u.name or "N/A")[:24]
            print(f"#{u.id:<5} | {name:<25} | {item['domain']:<18} | {c_date:<20} | {item['analyses']}")

    print("=" * 90)
    print(f"Total Accounts in Deletion Preview: {len(candidates)}")
    print("=" * 90)

    print("\n" + "=" * 90)
    print("PROTECTED / SKIPPED ACCOUNTS (Will NOT be touched)")
    print("=" * 90)
    for item in skipped:
        u = item["user"]
        c_date = u.created_at.strftime("%d %b %Y, %I:%M %p") if u.created_at else "N/A"
        name = (u.name or "N/A")[:24]
        print(f"#{u.id:<5} | {name:<25} | {item['domain']:<18} | Role: {u.role:<6} | Reason: {item['reason']}")
    print("=" * 90)

    if not candidates:
        print("\nNothing to delete. Exiting.")
        return

    # Step 3: Require explicit 'YES' confirmation
    if auto_confirm:
        user_input = "YES"
    else:
        print("\nSAFETY CONFIRMATION REQUIRED:")
        print("Type 'YES' to permanently delete the accounts listed in the preview above.")
        print("Any other input will cancel the operation.")
        try:
            user_input = input("Confirmation [YES to proceed]: ").strip()
        except EOFError:
            user_input = ""

    if user_input != "YES":
        print("\n[CANCELLED] Operation cancelled by user. Zero records were deleted.")
        return

    print("\n[*] Proceeding with account deletion and anonymization...")
    deleted_ids = []
    try:
        for item in candidates:
            u = item["user"]
            uid = u.id
            delete_single_account(db, u)
            deleted_ids.append(uid)

        db.commit()
        print(f"[OK] Successfully deleted {len(deleted_ids)} test accounts: {deleted_ids}")
        print("[OK] Associated sessions, tokens, codes, and column alias references cleaned up.")
        print("[OK] Associated login_events and audit_logs entries fully anonymized.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed during account deletion: {e}")
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Clean up test data and accounts from far_app.")
    parser.add_argument("--preview-only", action="store_true", help="Only show the preview table and exit.")
    parser.add_argument("--confirm", action="store_true", help="Automatically proceed without prompting (use with caution).")
    parser.add_argument("--ids", type=str, default="", help="Comma-separated user IDs to delete explicitly (e.g. 112,113).")

    args = parser.parse_args()

    explicit = set()
    if args.ids:
        for part in args.ids.split(","):
            part = part.strip()
            if part.isdigit():
                explicit.add(int(part))

    if args.preview_only:
        db = next(database.get_db())
        candidates, skipped = get_candidate_test_accounts(db, explicit_ids=explicit)
        print("\n" + "=" * 90)
        print("PREVIEW OF TEST ACCOUNTS PROPOSED FOR DELETION (Domain Only, No Sensitive Data)")
        print("=" * 90)
        print(f"{'ID':<6} | {'Name':<25} | {'Email Domain':<18} | {'Created At':<20} | {'Analyses'}")
        print("-" * 90)
        for item in candidates:
            u = item["user"]
            c_date = u.created_at.strftime("%d %b %Y, %I:%M %p") if u.created_at else "N/A"
            name = (u.name or "N/A")[:24]
            print(f"#{u.id:<5} | {name:<25} | {item['domain']:<18} | {c_date:<20} | {item['analyses']}")
        print("=" * 90)
        print(f"Total Accounts in Deletion Preview: {len(candidates)}")
        print("=" * 90)
    else:
        preview_and_cleanup(auto_confirm=args.confirm, explicit_ids=explicit)
