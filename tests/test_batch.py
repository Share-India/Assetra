import os, sys, glob, pandas as pd
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
from column_mapper import resolve_columns, CANONICAL_FIELDS, load_alias_cache
from calculator import process_file

def run_tests():
    test_dir = os.path.join(os.path.dirname(__file__), "sample_files")
    upload_files = sorted(glob.glob(os.path.join(test_dir, "*.xlsx")))
    print(f"Found {len(upload_files)} test files to process.\n")
    for file_path in upload_files:
        basename = os.path.basename(file_path)
        print(f"=== Processing {basename} ===")
        try:
            df = pd.read_excel(file_path)
            headers = df.columns.tolist()
            sample_data = df.head(10).values.tolist()
            mapping = resolve_columns(headers, sample_data)
            suggestions = mapping.get('suggestions', {})
            cat = suggestions.get('category', {})
            acq = suggestions.get('acquisition_value', {})
            cap = suggestions.get('capitalized_date', {})
            print(f"  Category Col: {cat.get('mapped_column')} (via {cat.get('method')})")
            print(f"  Acquisition Col: {acq.get('mapped_column')} (via {acq.get('method')})")
            print(f"  Date Col: {cap.get('mapped_column')} (via {cap.get('method')})")
        except Exception as e:
            print(f"  Error reading {basename}: {e}")

if __name__ == "__main__":
    run_tests()
