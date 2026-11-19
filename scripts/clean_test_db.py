"""
scripts/clean_test_db.py
Empties all application tables in far_app_test after test runs.
Strictly refuses to run if DB_NAME is far_app or not a test database.
"""
import os
import sys

# Ensure backend is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Enforce far_app_test
db_name = os.getenv("DB_NAME", "far_app_test")

if db_name == "far_app" or not db_name.endswith("_test"):
    print("\n" + "!" * 80, file=sys.stderr)
    print(f"CRITICAL SAFETY REFUSAL: clean_test_db.py cannot run against '{db_name}'!", file=sys.stderr)
    print("This script is strictly restricted to test databases such as 'far_app_test'.", file=sys.stderr)
    print("!" * 80 + "\n", file=sys.stderr)
    sys.exit(1)

# Set DB_NAME in environment so database.py picks it up
os.environ["DB_NAME"] = db_name

import database
from sqlalchemy import text

TABLES_TO_EMPTY = [
    "analysis_rows",
    "analyses",
    "user_sessions",
    "email_verification_codes",
    "password_reset_tokens",
    "login_events",
    "audit_logs",
    "audit_log",
    "user_column_mappings",
    "classification_cache",
    "column_alias_cache",
    "company_industry_cache",
    "users",
]

def clean_test_database():
    print(f"Starting test database cleanup for '{db_name}'...")
    db = next(database.get_db())
    try:
        # Verify connected database
        current_db = db.execute(text("SELECT DATABASE()")).scalar()
        if current_db != "far_app_test":
            print(f"ERROR: Connected to unexpected database '{current_db}'! Aborting.", file=sys.stderr)
            sys.exit(1)

        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        for table in TABLES_TO_EMPTY:
            db.execute(text(f"TRUNCATE TABLE `{table}`;"))
            print(f"  - Emptied table: {table}")
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.commit()
        print(f"Successfully emptied {len(TABLES_TO_EMPTY)} tables in '{current_db}'. Schema preserved.")
    except Exception as e:
        db.rollback()
        print(f"Error cleaning test database: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    clean_test_database()
