import sys, os, collections
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from calculator import process_file

candidates = [
    r'C:/Users/Ankita/Desktop/FAR/FAR_Fridabad.xlsx',
    r'C:/Users/Ankita/Desktop/FAR/FAR_Faridabad.xlsx',
    os.path.join(os.path.dirname(__file__), 'data', 'test_faridabad.xlsx')
]
file_path = next((c for c in candidates if os.path.exists(c)), None)

if file_path:
    print(f"Testing Faridabad using: {file_path}")
    result = process_file(file_path, 'All Commodities', {}, 0, '')
    print(f"Processed {len(result['mappedData'])} rows successfully.")
else:
    print("Faridabad test file not found in candidates.")
