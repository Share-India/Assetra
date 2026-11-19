"""
Test Database Isolation & Safety Guard
Enforces that tests NEVER run against production database 'far_app'.
"""
import os
import sys

def enforce_test_db():
    db_name = os.getenv("DB_NAME")
    if db_name == "far_app":
        banner = "!" * 78
        err_msg = (
            f"\n{banner}\n"
            "ERROR: SAFETY VIOLATION! Tests must refuse to run when DB_NAME is 'far_app'.\n"
            "All tests and test scripts must use 'far_app_test', never 'far_app'!\n"
            f"{banner}\n"
        )
        print(err_msg, file=sys.stderr)
        raise RuntimeError("SAFETY VIOLATION: Tests must refuse to run when DB_NAME is 'far_app'!")

    # Mark testing mode and default database to far_app_test
    os.environ["TESTING"] = "true"
    os.environ.setdefault("DB_NAME", "far_app_test")

# Run guard on import
enforce_test_db()
