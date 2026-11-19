import os, sys
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from calculator import process_file

test_file = os.path.join(os.path.dirname(__file__), "data", "test_far.xlsx")
if os.path.exists(test_file):
    res = process_file(test_file, "All Commodities")
    print(f"test_process.py: Processed {len(res['mappedData'])} rows successfully.")
else:
    print(f"File not found: {test_file}")
