import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables from backend/.env
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "far_app")
DB_USER = os.getenv("DB_USER", "far_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Guard: Tests must refuse to run against far_app
if os.getenv("TESTING", "").lower() in ("true", "1", "yes") and DB_NAME == "far_app":
    import sys
    err_msg = (
        "\n" + "!" * 80 + "\n"
        "ERROR: SAFETY VIOLATION! Tests must refuse to run when DB_NAME is 'far_app'.\n"
        "All tests and test scripts must use 'far_app_test', never 'far_app'!\n"
        "!" * 80 + "\n"
    )
    print(err_msg, file=sys.stderr)
    raise RuntimeError("SAFETY VIOLATION: Tests must refuse to run when DB_NAME is 'far_app'!")

import urllib.parse
encoded_user = urllib.parse.quote_plus(DB_USER)
encoded_password = urllib.parse.quote_plus(DB_PASSWORD)

# Build Database URL (never logged or printed)
DATABASE_URL = f"mysql+pymysql://{encoded_user}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
