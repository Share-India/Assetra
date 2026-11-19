import os
import json
import re
import math
import difflib
import datetime
import logging
import pandas as pd
from google import genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("far_backend.column_mapper")

CACHE_FILE = os.path.join(os.path.dirname(__file__), "data", "alias_cache.json")

DEFAULT_CANONICAL_FIELDS = {
    "asset_code": ["asset code", "asset id", "serial number", "tag no", "item code", "asset", "s no", "s.no"],
    "asset_description": ["asset description", "description", "particulars", "asset details", "asset desc", "item description", "item details", "equipment description"],
    "major_category": ["major category", "major cat", "asset group", "group", "category", "asset classification", "asset grouping"],
    "asset_class": ["asset class", "class", "nature of asset", "type", "class code"],
    "sub_category": ["sub category", "subcategory", "sub class", "asset class desc", "asset class description"],
    "acquisition_value": ["acquisition value", "acquis val", "purchase cost", "original cost", "gross block", "amount", "total cost", "cum acq value", "cost", "cost (inr)"],
    "capitalized_date": [
        "capitalized date", "capitalization date", "cap date", "cap. date", "capitalised date",
        "capitalisation date", "purchase date", "acquisition date", "capitalized on",
        "date of purchase", "put to use date", "date placed in service", "added on", "year", "capitalized year"
    ],
    "accumulated_depreciation": ["accumulated depreciation", "accum dep", "depreciation", "dep till date"],
    "book_value": ["book value", "wdv", "net block", "carrying value", "start book val", "end book val"],
    "currency": ["currency", "curr"],
    "location": ["location", "plant", "site", "unit", "risk location"]
}

CANONICAL_FIELDS = {}


def normalize_header(h):
    h = str(h).strip().lower()
    h = re.sub(r'[^a-z0-9]', ' ', h)
    h = re.sub(r'\s+', ' ', h)
    return h.strip()


def load_alias_cache():
    import copy
    CANONICAL_FIELDS.clear()
    CANONICAL_FIELDS.update(copy.deepcopy(DEFAULT_CANONICAL_FIELDS))

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                for k, v in cached.items():
                    if k in CANONICAL_FIELDS:
                        for item in v:
                            if item not in CANONICAL_FIELDS[k]:
                                CANONICAL_FIELDS[k].append(item)
                    else:
                        CANONICAL_FIELDS[k] = list(v)
        except Exception as e:
            logger.error(f"Error loading alias cache: {e}")

    # Also merge approved aliases from MySQL column_alias_cache
    try:
        from database import SessionLocal
        import models
        db = SessionLocal()
        try:
            approved_rows = db.query(models.ColumnAliasCache).filter(
                models.ColumnAliasCache.status == "approved",
                models.ColumnAliasCache.validation_passed == True
            ).all()
            for r in approved_rows:
                field = r.canonical_field
                norm_h = r.normalized_header
                if field and norm_h:
                    if field not in CANONICAL_FIELDS:
                        CANONICAL_FIELDS[field] = []
                    if norm_h not in CANONICAL_FIELDS[field]:
                        CANONICAL_FIELDS[field].append(norm_h)
        finally:
            db.close()
    except Exception:
        pass


def save_alias_cache():
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(CANONICAL_FIELDS, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving alias cache: {e}")


def fuzzy_match(normalized_header, aliases):
    best_score = 0.0
    for alias in aliases:
        score = difflib.SequenceMatcher(None, normalized_header, alias).ratio()
        if score > best_score:
            best_score = score
    return best_score


def _is_date_like_string(s: str) -> bool:
    s = str(s).strip()
    if not s:
        return False
    # ISO / slash / dash date patterns like 2021-05-01 or 14/06/2022
    if re.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}', s) or re.match(r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', s):
        return True
    if re.match(r'^(?:FY)?\s*\d{2}[-/]\d{2}$', s, re.IGNORECASE):
        return True
    return False


def _is_numeric_cost_value(val) -> bool:
    if val is None or pd.isna(val):
        return False
    if isinstance(val, (datetime.date, datetime.datetime)):
        return False
    if isinstance(val, (int, float)):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return False
        return True
    s = str(val).strip()
    if not s or s in ("-", "nan", "None", "null"):
        return False
    if _is_date_like_string(s):
        return False
    cleaned = re.sub(r'(?:rs\.?|inr|₹|\$|,|\s)', '', s, flags=re.IGNORECASE)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        float(cleaned)
        return True
    except Exception:
        return False


def _is_valid_date_or_year_value(val) -> bool:
    if val is None or pd.isna(val):
        return False
    if isinstance(val, (datetime.date, datetime.datetime)):
        return 1950 <= val.year <= 2030
    if isinstance(val, (int, float)):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return False
        # 4-digit year
        if 1950 <= val <= 2030:
            return True
        # Excel serial date (~1950 to ~2035 is 18264 to 49670)
        if 18000 <= val <= 50000 and float(val).is_integer():
            return True
        return False
    s = str(val).strip()
    if not s or s in ("-", "nan", "None", "null"):
        return False
    # 4-digit year string
    if re.match(r'^(19[5-9]\d|20[0-3]\d)(?:\.0)?$', s):
        return True
    if _is_date_like_string(s):
        return True
    # Pure number check (avoid treating arbitrary cost numbers like 42500.50 or 450000 as dates)
    cleaned_num = s.replace(",", "").strip()
    try:
        num = float(cleaned_num)
        if 1950 <= num <= 2030 and num.is_integer():
            return True
        return False
    except Exception:
        pass
    try:
        with pd.option_context("mode.chained_assignment", None):
            parsed = pd.to_datetime(s, errors="raise")
            if 1950 <= parsed.year <= 2030:
                return True
    except Exception:
        pass
    return False


def validate_column_choice(field: str, col_data: list, col_name: str = "") -> dict:
    """Validate whether col_data is suitable for the canonical field and return a plain-language warning if not."""
    non_empty = [
        v for v in (col_data or [])
        if v is not None and not (isinstance(v, float) and math.isnan(v))
        and str(v).strip() not in ("", "-", "nan", "None", "NaT")
    ]
    label_col = col_name or "Selected column"

    if field in ("major_category", "category", "sub_category", "asset_class"):
        if col_name in ("", "__NONE__", None):
            return {"valid": True, "warning": None, "ratio": 1.0}
        if not non_empty:
            return {
                "valid": False,
                "warning": f"'{label_col}' has no values in the sample rows.",
                "ratio": 0.0
            }
        return {"valid": True, "warning": None, "ratio": 1.0}

    if not non_empty:
        return {
            "valid": False,
            "warning": f"'{label_col}' is empty in the sample rows. Please choose a column that has data.",
            "ratio": 0.0
        }

    total = len(non_empty)

    if field in ("acquisition_value", "accumulated_depreciation", "book_value"):
        valid_count = sum(1 for v in non_empty if _is_numeric_cost_value(v))
        ratio = valid_count / total
        if ratio <= 0.8:
            pct = int(round(ratio * 100))
            return {
                "valid": False,
                "warning": (
                    f"Warning: '{label_col}' contains mostly text or non-cost values "
                    f"({pct}% numeric). The cost column must be mostly numeric."
                ),
                "ratio": ratio
            }
        return {"valid": True, "warning": None, "ratio": ratio}

    if field in ("capitalized_date", "purchase_date"):
        valid_count = sum(1 for v in non_empty if _is_valid_date_or_year_value(v))
        ratio = valid_count / total
        if ratio <= 0.5:
            pct = int(round(ratio * 100))
            return {
                "valid": False,
                "warning": (
                    f"Warning: '{label_col}' does not parse as dates or years "
                    f"({pct}% valid dates/years). Please choose a column with purchase dates or 4-digit years."
                ),
                "ratio": ratio
            }
        return {"valid": True, "warning": None, "ratio": ratio}

    if field == "asset_description":
        num_only_count = sum(1 for v in non_empty if _is_numeric_cost_value(v) or _is_valid_date_or_year_value(v))
        text_ratio = 1.0 - (num_only_count / total)
        if text_ratio < 0.2:
            return {
                "valid": False,
                "warning": (
                    f"Warning: '{label_col}' contains mostly numbers or dates instead of asset descriptions. "
                    f"Please pick the column that describes each asset."
                ),
                "ratio": text_ratio
            }
        return {"valid": True, "warning": None, "ratio": text_ratio}

    return {"valid": True, "warning": None, "ratio": 1.0}


def validate_content(field, col_data):
    if not col_data:
        return True
    non_empty = [
        v for v in col_data
        if v is not None and not (isinstance(v, float) and math.isnan(v))
        and str(v).strip() not in ("", "-", "nan", "None", "NaT")
    ]
    if not non_empty:
        return True
    total_count = len(non_empty)

    if field in ("acquisition_value", "accumulated_depreciation", "book_value"):
        valid_count = sum(1 for val in non_empty if _is_numeric_cost_value(val))
        return (valid_count / total_count) > 0.8

    elif field == "capitalized_date":
        valid_count = sum(1 for val in non_empty if _is_valid_date_or_year_value(val))
        return (valid_count / total_count) > 0.5

    elif field in ["category", "asset_class", "major_category"]:
        # Ensure it's not a pure date column or pure large currency column
        date_count = sum(1 for val in non_empty if _is_date_like_string(str(val)))
        if (date_count / total_count) > 0.6:
            return False
        return True

    elif field == "asset_code":
        unique_vals = set([str(x) for x in non_empty if pd.notna(x) and str(x).strip() != ""])
        return len(unique_vals) >= max(1, int(total_count * 0.5))

    return True


def generate_validation_summary(field: str, col_data: list) -> str:
    """
    Generate an aggregated validation summary without storing raw user values.
    Example: '100% numeric, 20 rows tested', '100% valid date/year, 15 rows tested', '100% text, 25 rows tested'.
    """
    if not col_data:
        return "No rows tested"
    non_empty = [
        v for v in col_data
        if v is not None and not (isinstance(v, float) and math.isnan(v))
        and str(v).strip() not in ("", "-", "nan", "None", "NaT")
    ]
    if not non_empty:
        return f"0 non-empty rows ({len(col_data)} tested)"

    total = len(non_empty)
    if field in ("acquisition_value", "accumulated_depreciation", "book_value"):
        valid_cnt = sum(1 for val in non_empty if _is_numeric_cost_value(val))
        pct = int(round((valid_cnt / total) * 100))
        return f"{pct}% numeric, {total} rows tested"
    elif field in ("capitalized_date", "purchase_date"):
        valid_cnt = sum(1 for val in non_empty if _is_valid_date_or_year_value(val))
        pct = int(round((valid_cnt / total) * 100))
        return f"{pct}% valid date/year, {total} rows tested"
    elif field in ("major_category", "category", "sub_category", "asset_class", "location", "asset_code", "asset_description"):
        num_or_date = sum(1 for val in non_empty if _is_numeric_cost_value(val) or _is_valid_date_or_year_value(val))
        text_cnt = total - num_or_date
        pct = max(0, min(100, int(round((text_cnt / total) * 100))))
        if field == "asset_description":
            return f"{pct}% text description, {total} rows tested"
        return f"{pct}% text, {total} rows tested"
    else:
        return f"100% valid, {total} rows tested"


def llm_fallback_batch(unmapped_headers_data):
    if os.getenv("MOCK_LLM") == "1":
        mock_map = {
            "block of assets": "category",
            "asset head": "category",
            "nature of asset": "category",
            "asset class": "category",
            "classification": "category",
            "asset sub-group": "category",
            "major cat.": "category"
        }
        results = {}
        for header in unmapped_headers_data.keys():
            mapped = mock_map.get(header.strip().lower(), "unknown")
            if mapped != "unknown":
                results[header] = (mapped, "LLM Confirmed (Mock)")
            else:
                results[header] = ("unknown", "LLM No Match (Mock)")
        return results

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return {h: ("unknown", "No API Key") for h in unmapped_headers_data.keys()}

    client = genai.Client(api_key=gemini_key)
    model = os.getenv("GEMINI_MODEL")

    fields_list = ", ".join(CANONICAL_FIELDS.keys())
    prompt = f"Map each of the following dataset columns to exactly one of these canonical fields: [{fields_list}].\n"
    prompt += "If a column doesn't match any canonical field, map it to 'unknown'.\n"
    prompt += "Return the mapping strictly as a JSON dictionary where keys are the column headers and values are the mapped canonical fields.\n\n"

    for header, sample_data in unmapped_headers_data.items():
        prompt += f"Column Header: '{header}'\n"
        prompt += f"Sample Data: {sample_data[:5]}\n\n"

    import time

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )

            try:
                mapping = json.loads(response.text)
            except json.JSONDecodeError as je:
                logger.warning(f"LLM Fallback JSON parsing failed: {je}")
                return {h: ("unknown", "LLM Malformed JSON") for h in unmapped_headers_data.keys()}

            results = {}
            for header in unmapped_headers_data.keys():
                mapped = str(mapping.get(header, "unknown")).strip().lower()
                if mapped in CANONICAL_FIELDS:
                    results[header] = (mapped, "LLM Confirmed")
                else:
                    results[header] = ("unknown", "LLM No Match")
            return results
        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < max_retries:
                sleep_time = (attempt + 1) * 3
                logger.warning(f"LLM Fallback 429 error. Retrying in {sleep_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(sleep_time)
                continue

            logger.error(f"LLM Fallback error: {e}")
            return {h: ("unknown", f"LLM Error: {e}") for h in unmapped_headers_data.keys()}


def resolve_columns(headers, sample_rows):
    load_alias_cache()

    results = {}
    used_indices = set()

    cols_data = [[] for _ in headers]
    if sample_rows:
        for row in sample_rows:
            for i, val in enumerate(row):
                if i < len(cols_data):
                    cols_data[i].append(val)

    for field in CANONICAL_FIELDS.keys():
        results[field] = {"mapped_column": None, "confidence": "NONE", "method": "NONE", "score": 0.0}

    # Pass 1: Exact Match against approved aliases
    for i, h in enumerate(headers):
        if i in used_indices:
            continue
        norm_h = normalize_header(h)
        if not norm_h:
            continue
        for field, aliases in CANONICAL_FIELDS.items():
            if results[field]["mapped_column"]:
                continue
            if norm_h in aliases:
                if validate_content(field, cols_data[i]):
                    results[field] = {"mapped_column": h, "confidence": "HIGH", "method": "EXACT", "score": 1.0}
                    used_indices.add(i)
                    break

    # Pass 2: Fuzzy Match (MEDIUM confidence -> requires user check; DO NOT auto-write to shared cache)
    for i, h in enumerate(headers):
        if i in used_indices:
            continue
        norm_h = normalize_header(h)
        if not norm_h:
            continue

        best_field = None
        best_score = 0.0

        for field, aliases in CANONICAL_FIELDS.items():
            if results[field]["mapped_column"]:
                continue
            score = fuzzy_match(norm_h, aliases)
            if score > best_score:
                best_score = score
                best_field = field

        if best_field and best_score > 0.8:
            if validate_content(best_field, cols_data[i]):
                results[best_field] = {"mapped_column": h, "confidence": "MEDIUM", "method": "FUZZY", "score": best_score}
                used_indices.add(i)

    # Synchronize 'category' / 'asset_class' / 'sub_category' into 'major_category' if 'major_category' was not matched directly
    if not results.get("major_category", {}).get("mapped_column"):
        if results.get("category", {}).get("mapped_column"):
            results["major_category"] = dict(results["category"])
        elif results.get("asset_class", {}).get("mapped_column"):
            results["major_category"] = dict(results["asset_class"])
            results["category"] = dict(results["asset_class"])
        elif results.get("sub_category", {}).get("mapped_column"):
            results["major_category"] = dict(results["sub_category"])
            results["category"] = dict(results["sub_category"])
    elif not results.get("category", {}).get("mapped_column"):
        results["category"] = dict(results["major_category"])

    # Pass 3: LLM Fallback (only for Required/Recommended Fields that are still missing)
    required_fields = ["major_category", "acquisition_value", "capitalized_date", "asset_description"]
    missing_required = [f for f in required_fields if not results.get(f, {}).get("mapped_column")]

    if missing_required:
        unmapped_headers_data = {}
        for i, h in enumerate(headers):
            if i not in used_indices and str(h).strip() != "":
                unmapped_headers_data[h] = cols_data[i]

        if unmapped_headers_data:
            batch_results = llm_fallback_batch(unmapped_headers_data)

            for i, h in enumerate(headers):
                if i in used_indices:
                    continue

                matched_field, note = batch_results.get(h, ("unknown", "No Match"))
                if matched_field == "category" and not results.get("major_category", {}).get("mapped_column"):
                    matched_field = "major_category"

                if matched_field in CANONICAL_FIELDS and not results[matched_field]["mapped_column"]:
                    if validate_content(matched_field, cols_data[i]):
                        results[matched_field] = {"mapped_column": h, "confidence": "LOW", "method": "LLM", "score": 0.9}
                        used_indices.add(i)
                        if matched_field in missing_required:
                            missing_required.remove(matched_field)

    # Final sync between category and major_category
    if not results.get("major_category", {}).get("mapped_column") and results.get("category", {}).get("mapped_column"):
        results["major_category"] = dict(results["category"])
    elif not results.get("category", {}).get("mapped_column") and results.get("major_category", {}).get("mapped_column"):
        results["category"] = dict(results["major_category"])

    return {
        "suggestions": results,
        "unmapped_columns": [h for i, h in enumerate(headers) if i not in used_indices]
    }


load_alias_cache()
