import sys, os, pandas as pd
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from calculator import process_file

test_file = os.path.join(os.path.dirname(__file__), "data", "test_far.xlsx")
if not os.path.exists(test_file):
    test_file = os.path.join(os.path.dirname(__file__), "test_far.xlsx")

if os.path.exists(test_file):
    print(f"Starting process_file with {test_file}...")
    result = process_file(test_file, 'All Commodities')
    for r in result.get('mappedData', [])[:5]:
        print(f"Asset: {r.get('assetCode')}, Py: {r.get('purchaseYear')}, Acq: {r.get('acquisitionValue')}, Rep: {r.get('replacementValue')}")
else:
    print(f"Test file not found at {test_file}")
