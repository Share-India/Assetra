import sys, os
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from column_mapper import resolve_columns, CANONICAL_FIELDS

def test():
    past_headers = [
        ["Major Cat.", "Asset Class", "Asset Class Desc."],
        ["Category", "Acquis.val.", "Capitalized on", "Asset   description"]
    ]
    for idx, headers in enumerate(past_headers):
        print(f"\n--- Testing File {idx+1} Headers: {headers} ---")
        res = resolve_columns(headers, None)
        import pprint
        pprint.pprint(res['suggestions'])

if __name__ == "__main__":
    test()
