"""
scripts/verify_benchmarks.py
Runs the four benchmark FAR files through calculator.process_file and compares
against tests/data/baseline_results.json to confirm 0 differing rows.
"""
import os
import sys
import json
import contextlib
import io

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from calculator import process_file, load_datasets

def run_benchmark_verification():
    print("=" * 105)
    print("           BENCHMARK FAR ACCURACY & REGRESSION TEST AGAINST BASELINE (0 DIFFERING ROWS)          ")
    print("=" * 105)
    
    with contextlib.redirect_stdout(io.StringIO()):
        load_datasets()
    
    baseline_path = os.path.join(os.path.dirname(__file__), "..", "tests", "data", "baseline_results.json")
    if not os.path.exists(baseline_path):
        print(f"ERROR: Baseline file not found at {baseline_path}", file=sys.stderr)
        sys.exit(1)
        
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    benchmarks = [
        ("Faridabad", r"C:\Users\Ankita\Desktop\FAR\FAR_Fridabad.xlsx"),
        ("Rudrapur", r"C:\Users\Ankita\Desktop\FAR\FAR_Rudrapur.xlsx"),
        ("HOCP", r"C:\Users\Ankita\Desktop\FAR\FAR_HOCP.xlsx"),
        ("Pure & Cure", r"C:\Users\Ankita\Desktop\FAR\Pure & Cure Healthcare Pvt.Ltd..xlsx"),
    ]

    all_passed = True
    results_summary = []

    for b_name, b_path in benchmarks:
        if not os.path.exists(b_path):
            print(f"ERROR: File not found for {b_name}: {b_path}", file=sys.stderr)
            all_passed = False
            continue

        with contextlib.redirect_stdout(io.StringIO()):
            res_b = process_file(b_path, "All Commodities (General Index)")
            
        actual_rows = res_b["mappedData"]
        expected_rows = baseline[b_name]
        diff_count = 0
        
        if len(actual_rows) != len(expected_rows):
            diff_count = abs(len(actual_rows) - len(expected_rows))
        else:
            for r_act, r_exp in zip(actual_rows, expected_rows):
                g_act = r_act.get("wpiGroup")
                g_exp = r_exp.get("group")
                rv_act = r_act.get("replacementValue")
                rv_exp = r_exp.get("replacementValue")
                pw_act = r_act.get("purchaseWpi")
                pw_exp = r_exp.get("purchaseWpi")
                cw_act = r_act.get("currentWpi")
                cw_exp = r_exp.get("currentWpi")

                row_diff = False
                if g_act != g_exp:
                    row_diff = True
                for v1, v2 in ((rv_act, rv_exp), (pw_act, pw_exp), (cw_act, cw_exp)):
                    try:
                        if abs(float(v1) - float(v2)) > 0.05:
                            row_diff = True
                    except (ValueError, TypeError):
                        if str(v1).strip() != str(v2).strip():
                            row_diff = True
                if row_diff:
                    diff_count += 1

        acq_val = res_b["metrics"]["Total Acquisition Value"]
        rep_val = res_b["metrics"]["Total Replacement Value"]
        status = "PASSED (0 diff)" if diff_count == 0 else f"FAILED ({diff_count} diff)"
        
        print(
            f"Benchmark: {b_name:<12} | Rows: {len(actual_rows):<6} (Baseline: {len(expected_rows):<6}) "
            f"| Total Acq: ₹{acq_val:>15,.2f} | Total Rep: ₹{rep_val:>15,.2f} "
            f"| Differing Rows: {diff_count:<4} | {status}"
        )
        results_summary.append((b_name, len(actual_rows), diff_count, status))
        if diff_count != 0:
            all_passed = False

    print("=" * 105)
    if all_passed:
        print("RESULT: ALL 4 BENCHMARK FARS PRODUCE EXACTLY 0 DIFFERING ROWS AGAINST BASELINE.")
    else:
        print("RESULT: DIFFERENCES DETECTED!")
        sys.exit(1)

if __name__ == "__main__":
    run_benchmark_verification()
