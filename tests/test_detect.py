import sys, os
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from column_mapper import resolve_columns as detect_columns

headers = [
    "Company Code", "Business Area", "Asset", "Sub-number", "Capitalized on",
    "Asset   description", "Acquis.val.", "Accum.dep.", "Book val.", "Currency",
    "Asset Class", "Asset Class Desc.", "Risk Location ", "Insured Name",
    "Asset Grouping", "Sr.", "Note", "RIV"
]

res = detect_columns(headers, None)
import pprint
pprint.pprint(res)
