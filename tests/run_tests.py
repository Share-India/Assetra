import os, sys, pandas as pd
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from calculator import process_file

faridabad_candidates = [
    os.path.join(os.path.dirname(__file__), "data", "test_faridabad.xlsx"),
    r"C:\Users\Ankita\Desktop\FAR\FAR_Fridabad.xlsx",
    r"C:\Users\Ankita\Desktop\FAR\FAR_Faridabad.xlsx"
]
faridabad_file = next((c for c in faridabad_candidates if os.path.exists(c)), None)

if faridabad_file:
    print(f"Running test on: {faridabad_file}")
    res = process_file(faridabad_file, 'All Commodities', {}, 0, '')
    print(f"Result count: {len(res['mappedData'])} assets processed.")
else:
    print("No Faridabad test file found.")
