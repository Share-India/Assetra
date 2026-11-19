import sys, os
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from column_mapper import resolve_columns

headers = [
    "Company Code", "Business Area", "Asset", "Sub-number", "Capitalized on",
    "Asset   description", "Acquis.val.", "Accum.dep.", "Book val.", "Currency",
    "Asset Class", "Asset Class Desc.", "Risk Location ", "Insured Name",
    "Asset Grouping", "Sr.", "Note", "RIV"
]

sample_rows = [
    ["1000", "HQ", "12345", "0", "2021-05-01", "Macbook Pro", "150000", "50000", "100000", "INR", "IT", "Computer enduser", "Mumbai", "LIC", "Office Equip", "1", "", "200000"],
    ["1000", "HQ", "12346", "0", "2020-03-15", "Office Chair", "15000", "5000", "10000", "INR", "Furn", "Furniture", "Delhi", "LIC", "Furniture", "2", "", "20000"],
    ["1000", "HQ", "12347", "0", "2019-10-10", "Server rack", "500000", "200000", "300000", "INR", "IT", "Servers", "Mumbai", "LIC", "Plant & Mach", "3", "", "600000"]
]

res = resolve_columns(headers, sample_rows)
import pprint
pprint.pprint(res)
