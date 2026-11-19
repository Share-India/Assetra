import sys, os
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from calculator import normalize_text, process_file

cats = ["computer(enduser)", "computer(server,networking)", "low value assets-servers,networking"]
print("Normalizations:")
for c in cats:
    print(f"'{c}' -> '{normalize_text(c)}'")
