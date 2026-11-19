import os, sys
from dotenv import load_dotenv

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
load_dotenv(os.path.join(BACKEND_DIR, '.env'))

print("--- STARTUP CHECK ---")
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
print(f"Configured Model: {model}")
from calculator import load_datasets, VALID_WPI_GROUPS
load_datasets()
print(f"Valid WPI Groups loaded count: {len(VALID_WPI_GROUPS)}")
