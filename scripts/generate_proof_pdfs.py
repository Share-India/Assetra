import os
import sys
import shutil

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import SessionLocal
import models
from pdf_summary_generator import generate_pdf_summary_stream, fetch_grouped_data

PROOF_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "proof_pdfs"))
ARTIFACT_DIR = r"C:\Users\Ankita\.gemini\antigravity\brain\3dce5edc-f8ef-40e4-8389-8171ef3eff54\proof_pdfs"

os.makedirs(PROOF_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

benchmarks = [
    {"name": "Faridabad", "id": 10},
    {"name": "Rudrapur", "id": 7},
    {"name": "HOCP", "id": 5},
    {"name": "Pure & Cure", "id": 28},
]

def generate_all():
    db = SessionLocal()
    try:
        print("=" * 115)
        print("             VALUATION SUMMARY PDF vs DASHBOARD TOTALS RECONCILIATION             ")
        print("=" * 115)
        print(f"{'Benchmark':<15} | {'Metric':<18} | {'Dashboard Value':>25} | {'PDF Grand Total':>25} | {'Difference':>12} | Status")
        print("-" * 115)

        all_matched = True

        for b in benchmarks:
            analysis_id = b["id"]
            name = b["name"]

            analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
            if not analysis:
                print(f"ERROR: Analysis ID {analysis_id} not found!")
                all_matched = False
                continue

            # Fetch grouped data for verification
            grand_total_rows, location_rows, distinct_locations, held_at_cost = fetch_grouped_data(db, analysis_id)
            
            # Calculate grand total sums across grand_total_rows
            pdf_count = sum(r["count"] for r in grand_total_rows)
            pdf_acq = sum(r["cost"] for r in grand_total_rows)
            pdf_rep = sum(r["replacement"] for r in grand_total_rows)

            dash_count = analysis.rows_total
            diff_count = pdf_count - dash_count

            dash_acq = float(analysis.total_acquisition or 0.0)
            diff_acq = pdf_acq - dash_acq

            dash_rep = float(analysis.total_replacement or 0.0)
            diff_rep = pdf_rep - dash_rep

            status_cnt = "MATCH" if diff_count == 0 else "MISMATCH"
            status_acq = "MATCH" if abs(diff_acq) < 0.001 else "MISMATCH"
            status_rep = "MATCH" if abs(diff_rep) < 0.001 else "MISMATCH"

            if status_cnt != "MATCH" or status_acq != "MATCH" or status_rep != "MATCH":
                all_matched = False

            print(f"{name:<15} | {'Asset Count':<18} | {dash_count:>25,d} | {pdf_count:>25,d} | {diff_count:>12d} | {status_cnt}")
            print(f"{'':<15} | {'Acquisition (INR)':<18} | {dash_acq:>25,.2f} | {pdf_acq:>25,.2f} | {diff_acq:>12.2f} | {status_acq}")
            print(f"{'':<15} | {'Replacement (INR)':<18} | {dash_rep:>25,.2f} | {pdf_rep:>25,.2f} | {diff_rep:>12.2f} | {status_rep}")
            print("-" * 115)

            # Generate PDF
            pdf_stream = generate_pdf_summary_stream(analysis, db)
            pdf_bytes = pdf_stream.getvalue()

            file_name = f"Valuation_Summary_{name.replace(' ', '_')}.pdf"
            out_path1 = os.path.join(PROOF_DIR, file_name)
            out_path2 = os.path.join(ARTIFACT_DIR, file_name)

            with open(out_path1, "wb") as f:
                f.write(pdf_bytes)
            with open(out_path2, "wb") as f:
                f.write(pdf_bytes)

            print(f"Generated PDF ({len(pdf_bytes):,d} bytes): {out_path1}")

        print("=" * 115)
        if all_matched:
            print("RECONCILIATION RESULT: ALL DASHBOARD TOTALS AND PDF GRAND TOTALS MATCH EXACTLY TO THE PAISA.")
        else:
            print("RECONCILIATION RESULT: MISMATCHES DETECTED!")
            sys.exit(1)

    finally:
        db.close()

if __name__ == "__main__":
    generate_all()
