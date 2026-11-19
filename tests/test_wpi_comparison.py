import sys, os, pandas as pd, json
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
import calculator

TEST_FILE = os.path.join(os.path.dirname(__file__), 'data', 'test_cases.xlsx')
if os.path.exists(TEST_FILE):
    print("=== RUNNING WPI COMPARISON TEST ===")
    result = calculator.process_file(TEST_FILE, "All Commodities")
    print(f"Successfully processed {len(result['mappedData'])} rows from test_cases.xlsx")
else:
    print(f"Test cases file not found at {TEST_FILE}")
