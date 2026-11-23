import os
import sys
import hashlib
import datetime
import math

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import SessionLocal
import models
from calculator import process_file, load_datasets
from routers.analyses import get_master_version_hash

def extract_original_row_dict(raw, headers):
    orig_dict = {}
    if isinstance(raw, list):
        for col_idx, col_name in enumerate(headers):
            if col_idx < len(raw):
                val = raw[col_idx]
                if val is not None:
                    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                        continue
                    if isinstance(val, (datetime.date, datetime.datetime)):
                        orig_dict[col_name] = val.isoformat()
                    else:
                        orig_dict[col_name] = val
    elif isinstance(raw, dict):
        orig_dict = raw
    return orig_dict

def populate_pure_and_cure():
    file_path = r"C:\Users\Ankita\Desktop\FAR\Pure & Cure Healthcare Pvt.Ltd..xlsx"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    db = SessionLocal()
    try:
        existing = db.query(models.Analysis).filter(
            models.Analysis.original_filename == "Pure & Cure Healthcare Pvt.Ltd..xlsx"
        ).first()
        if existing:
            print(f"Pure & Cure analysis already exists: ID {existing.id}")
            return existing.id

        with open(file_path, "rb") as f:
            file_bytes = f.read()
        file_sha256 = hashlib.sha256(file_bytes).hexdigest()

        load_datasets()
        master_version = get_master_version_hash()

        print("Processing Pure & Cure file...")
        result = process_file(file_path, "All Commodities (General Index)")
        metrics = result.get("metrics", {})
        mapped_data = result.get("mappedData", [])
        headers = result.get("headers", [])

        # Assign to user 73 (chauhanankitavirendra@gmail.com)
        analysis = models.Analysis(
            user_id=73,
            company_name="Pure & Cure Healthcare Pvt. Ltd.",
            industry="Healthcare / Pharma",
            original_filename="Pure & Cure Healthcare Pvt.Ltd..xlsx",
            file_sha256=file_sha256,
            master_version=master_version,
            columns_order=headers,
            status="completed",
            rows_total=metrics.get("Total Assets", len(mapped_data)),
            rows_calculated=metrics.get("Calculated Assets", 0),
            rows_manual_review=metrics.get("Manual Review Count", 0),
            rows_not_applicable=metrics.get("Not Applicable Count", 0),
            total_acquisition=metrics.get("Total Acquisition Value", 0.0),
            total_replacement=metrics.get("Total Replacement Value", 0.0),
            gemini_calls=metrics.get("gemini_calls", 0),
            completed_at=datetime.datetime.utcnow()
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        analysis_id = analysis.id
        print(f"Created Analysis ID: {analysis_id}")

        BATCH_SIZE = 1000
        for i in range(0, len(mapped_data), BATCH_SIZE):
            chunk = mapped_data[i:i + BATCH_SIZE]
            row_models = []
            for idx_in_chunk, r in enumerate(chunk):
                row_no = i + idx_in_chunk + 1
                acq_val = r.get("acquisitionValue")
                diff_val = r.get("difference")
                inc_pct = None
                if acq_val and diff_val is not None:
                    try:
                        inc_pct = float(diff_val) / float(acq_val)
                    except Exception:
                        inc_pct = 0.0
                elif r.get("status") in ["Success", "Not Applicable"]:
                    inc_pct = 0.0

                row_models.append(
                    models.AnalysisRow(
                        analysis_id=analysis_id,
                        row_no=row_no,
                        asset_code=str(r.get("assetCode") or "") if r.get("assetCode") is not None else None,
                        description=str(r.get("description") or "") if r.get("description") is not None else None,
                        capitalized_date=str(r.get("capDate") or "") if r.get("capDate") is not None else None,
                        purchase_year=r.get("purchaseYear") if isinstance(r.get("purchaseYear"), int) else None,
                        acquisition_value=acq_val if isinstance(acq_val, (int, float)) else None,
                        accumulated_dep=r.get("accumDep") if isinstance(r.get("accumDep"), (int, float)) else None,
                        book_value=r.get("bookValue") if isinstance(r.get("bookValue"), (int, float)) else None,
                        major_category=str(r.get("majorCategory") or "") if r.get("majorCategory") is not None else None,
                        sub_category=str(r.get("subCategory") or "") if r.get("subCategory") is not None else None,
                        asset_class=str(r.get("assetClass") or "") if r.get("assetClass") is not None else None,
                        location=str(r.get("location") or "") if r.get("location") is not None else None,
                        wpi_group=str(r.get("wpiGroup") or "") if r.get("wpiGroup") is not None else None,
                        wpi_series="SERIES_2011-12" if r.get("calculationMethod") == "WPI Based" else None,
                        purchase_wpi=r.get("purchaseWpi") if isinstance(r.get("purchaseWpi"), (int, float)) else None,
                        current_wpi=r.get("currentWpi") if isinstance(r.get("currentWpi"), (int, float)) else None,
                        calculation_method=str(r.get("calculationMethod") or "") if r.get("calculationMethod") is not None else None,
                        status=str(r.get("status") or "") if r.get("status") is not None else None,
                        note=str(r.get("note") or "") if r.get("note") is not None else None,
                        replacement_value=r.get("replacementValue") if isinstance(r.get("replacementValue"), (int, float)) else None,
                        difference=diff_val if isinstance(diff_val, (int, float)) else None,
                        increase_pct=inc_pct,
                        original_row=extract_original_row_dict(r.get("rawRow"), headers)
                    )
                )
            db.bulk_save_objects(row_models)
            db.commit()

        print(f"Successfully populated {len(mapped_data)} rows for Pure & Cure (Analysis ID {analysis_id}).")
        return analysis_id
    finally:
        db.close()

if __name__ == "__main__":
    populate_pure_and_cure()
