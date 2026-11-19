import logging
logger = logging.getLogger("far_backend.calculator")
import pandas as pd
from column_mapper import resolve_columns
from mixed_type_handler import process_mixed_type_columns

import json
import re

def normalize_text(text):
    text = str(text).strip().lower()
    text = re.sub(r'&', ' and ', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    tokens = text.split()
    norm_tokens = []
    for t in tokens:
        if t.endswith('ies') and len(t) > 4:
            t = t[:-3] + 'y'
        elif t.endswith('s') and not t.endswith('ss') and len(t) > 3:
            t = t[:-1]
        norm_tokens.append(t)
    return ' '.join(norm_tokens)
import difflib
import datetime

LATEST_WPI_YEAR = 2025
LATEST_SERIES = 'SERIES_2011-12'
HEADLINE_WPI_GROUP = "All Commodities (headline)"

BUILDING_ESCALATION_RATE = 0.05
LAND_ESCALATION_RATE = 0.05

import os
REFERENCE_YEAR = 2025

STAGE_END_YEAR = {
    "1961-62": 1970,
    "1970-71": 1982,
    "1981-82": 1994,
    "1994-95": 2004,
    "2004-05": 2011,
    "2011-12": REFERENCE_YEAR
}

STAGE_START_YEAR = {
    "1961-62": 1961,
    "1970-71": 1970,
    "1981-82": 1981,
    "1994-95": 1994,
    "2004-05": 2004,
    "2011-12": 2011
}

# The ordered list of stages
STAGES_ORDERED = [
    "1961-62",
    "1970-71",
    "1981-82",
    "1994-95",
    "2004-05",
    "2011-12"
]
import math
import time

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

WPI_DATA = None





def load_datasets(force: bool = False):
    global WPI_DATA
    global VALID_WPI_GROUPS
    global REFERENCE_YEAR, LATEST_WPI_YEAR, BUILDING_ESCALATION_RATE, LAND_ESCALATION_RATE
    import time
    if WPI_DATA is not None and not force:
        return

    v6_candidate = os.path.join(DATA_DIR, "WPI_MASTER_DATASET_CATEGORYWISE_v6.xlsx")
    default_candidate = os.path.join(DATA_DIR, "WPI_MASTER_DATASET_CATEGORYWISE.xlsx")
    if os.path.exists(v6_candidate):
        filepath = v6_candidate
    elif os.path.exists(default_candidate):
        filepath = default_candidate
    else:
        filepath = default_candidate

    if not os.path.exists(filepath):
        logger.error(f"[WPI ERROR] Master dataset could not be loaded from {filepath}.")
        return

    try:
        xl = pd.ExcelFile(filepath)
        WPI_DATA = {} # Dictionary mapping stage name to its DataFrame

        # Make sure only sheets whose name contains "base" are loaded as year sheets
        for sheet in xl.sheet_names:
            if 'base' in sheet.lower():
                # Extract the stage name by stripping out ' base' and any extra text
                # e.g., '1994-95 base (official 1993-94)' -> '1994-95'
                stage_name = sheet.split(' ')[0]
                
                df = pd.read_excel(xl, sheet_name=sheet)

                # Identify year columns
                year_cols = [c for c in df.columns if str(c).isdigit()]

                if 'Category' in df.columns:
                    # Keep Category and Tier
                    cols_to_keep = ['Category']
                    if 'Tier' in df.columns:
                        cols_to_keep.append('Tier')
                    cols_to_keep.extend(year_cols)
                    
                    df_stage = df[cols_to_keep].copy()
                    
                    # Deduplicate categories just in case
                    df_stage = df_stage.groupby('Category', as_index=False).first()
                    df_stage.set_index('Category', inplace=True)
                    
                    # Ensure year columns are strings
                    col_map = {c: str(c) for c in df_stage.columns if isinstance(c, (int, float)) or str(c).isdigit()}
                    df_stage.rename(columns=col_map, inplace=True)

                    WPI_DATA[stage_name] = df_stage

        logger.info("--- WPI Master Dataset Initialization ---")
        logger.info(f"Path: {filepath}")
        mod_time = os.path.getmtime(filepath)
        logger.info(f"Modified: {time.ctime(mod_time)}")
        logger.info(f"Loaded {len(WPI_DATA)} base year sheets: {list(WPI_DATA.keys())}")
        
        # Read valid group names from the ASSET_GROUPS sheet (unique 'Asset Group' values, plus All commodities)
        VALID_WPI_GROUPS = []
        if 'ASSET_GROUPS' in xl.sheet_names:
            df_ag = pd.read_excel(xl, sheet_name='ASSET_GROUPS')
            group_cols = [c for c in df_ag.columns if 'asset group' in str(c).lower()]
            group_col = group_cols[0] if group_cols else df_ag.columns[0]
            raw_groups = [str(g).strip() for g in df_ag[group_col].dropna().unique() if str(g).strip()]
            
            for g in raw_groups:
                if g not in VALID_WPI_GROUPS:
                    VALID_WPI_GROUPS.append(g)
            if "All commodities" not in VALID_WPI_GROUPS:
                VALID_WPI_GROUPS.append("All commodities")
                
            logger.info(f"Valid Groups Extracted ({len(VALID_WPI_GROUPS)}):")
            for g in VALID_WPI_GROUPS:
                logger.info(f" - {g}")

            # For any group and sheet marked "No data in this sheet", print a warning
            status_cols = [c for c in df_ag.columns if 'status' in str(c).lower()]
            sheet_cols = [c for c in df_ag.columns if 'sheet' in str(c).lower()]
            if status_cols and sheet_cols:
                s_col = status_cols[0]
                sh_col = sheet_cols[0]
                for _, r in df_ag.iterrows():
                    st_val = str(r[s_col]).strip()
                    if 'no data in this sheet' in st_val.lower():
                        logger.warning(f"[WPI WARNING] No data in this sheet: Group '{r[group_col]}' in sheet '{r[sh_col]}'")

        # Optional: Read reference year and Building/Land rate from the RULES sheet
        if 'RULES' in xl.sheet_names:
            df_rules = pd.read_excel(xl, sheet_name='RULES')
            rule_cols = [c for c in df_rules.columns if 'rule' in str(c).lower()]
            action_cols = [c for c in df_rules.columns if 'what the app does' in str(c).lower() or 'action' in str(c).lower()]
            if rule_cols and action_cols:
                r_col = rule_cols[0]
                a_col = action_cols[0]
                for _, r in df_rules.iterrows():
                    r_name = str(r[r_col]).lower()
                    action_text = str(r[a_col])
                    if 'reference' in r_name and 'year' in r_name:
                        m = re.search(r'\b(20\d\d)\b', action_text)
                        if m:
                            REFERENCE_YEAR = int(m.group(1))
                            LATEST_WPI_YEAR = REFERENCE_YEAR
                            STAGE_END_YEAR["2011-12"] = REFERENCE_YEAR
                            logger.info(f"[RULES] Reference Year loaded from RULES sheet: {REFERENCE_YEAR}")
                    elif 'building' in r_name:
                        m = re.search(r'(\d+(?:\.\d+)?)\s*%', action_text)
                        if m:
                            BUILDING_ESCALATION_RATE = float(m.group(1)) / 100.0
                            logger.info(f"[RULES] Building Escalation Rate loaded from RULES sheet: {BUILDING_ESCALATION_RATE:.2%}")
                    elif 'land' in r_name:
                        m = re.search(r'(\d+(?:\.\d+)?)\s*%', action_text)
                        if m:
                            LAND_ESCALATION_RATE = float(m.group(1)) / 100.0
                            logger.info(f"[RULES] Land Escalation Rate loaded from RULES sheet: {LAND_ESCALATION_RATE:.2%}")

        logger.info("-----------------------------------------")
            
    except Exception as e:
        logger.error(f"[WPI ERROR] Master dataset could not be loaded. {e}")

VALID_WPI_GROUPS = []
WPI_DATA = None
load_datasets()

import json
import re

def normalize_text(text):
    text = str(text).strip().lower()
    text = re.sub(r'&', ' and ', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    tokens = text.split()
    norm_tokens = []
    for t in tokens:
        if t.endswith('ies') and len(t) > 4:
            t = t[:-3] + 'y'
        elif t.endswith('s') and not t.endswith('ss') and len(t) > 3:
            t = t[:-1]
        norm_tokens.append(t)
    return ' '.join(norm_tokens)

SYNONYM_MAPPING = {}
DESCRIPTION_KEYWORDS = {}

def load_category_synonyms():
    global SYNONYM_MAPPING, DESCRIPTION_KEYWORDS
    syn_file = os.path.join(os.path.dirname(__file__), 'category_synonyms.json')
    try:
        with open(syn_file, 'r', encoding='utf-8') as f:
            _syn_data = json.load(f)
            SYNONYM_MAPPING = {normalize_text(k): _syn_data['SYNONYM_MAPPING'][k] for k in sorted(_syn_data['SYNONYM_MAPPING'].keys(), key=len, reverse=True)}
            DESCRIPTION_KEYWORDS = {k.strip().lower(): _syn_data['DESCRIPTION_KEYWORDS'][k] for k in sorted(_syn_data['DESCRIPTION_KEYWORDS'].keys(), key=len, reverse=True)}
    except Exception as e:
        logger.error(f"Failed to load category_synonyms.json: {e}")
        SYNONYM_MAPPING = {}
        DESCRIPTION_KEYWORDS = {}

load_category_synonyms()



load_datasets()



# Asset classification removed as per user instruction

FIELD_ALIASES = {
    "asset_description": [
        "asset description", "description", "particulars", "asset details",
        "asset desc", "item description", "item", "asset name", "name of asset"
    ],
    "purchase_date": [
        "purchase date", "acquisition date", "cap date", "cap. date", "cap.date",
        "date of acquisition", "date of purchase", "date of use", "capitalization date",
        "capitalisation date", "put to use date", "date of put to use", "doi", "dop",
        "capitalized on"
    ],
    "acquisition_value": [
        "acquisition value", "acquis. val.", "acquis.val.", "purchase cost",
        "original cost", "historical cost", "cost", "gross value", "gross block",
        "cost of acquisition", "purchase value", "amount", "total cost", "initial cost",
        "cum.acq.value", "cum acq value"
    ],
    "major_category": [
        "major category", "major cat", "major cat.", "asset group", "group", "category",
        "asset category", "asset classification", "asset grouping"
    ],
    "asset_class": [
        "asset class", "class", "nature of asset", "type"
    ],
    "asset_code": [
        "asset code", "asset unique code", "serial number", "asset id", "item code",
        "tag no", "tag number", "equipment id", "sno", "s.no", "asset"
    ],
    "sub_category": [
        "sub category", "subcategory", "sub-category", "sub group", "sub class", "asset class desc.", "asset class desc"
    ],
    "location": [
        "location", "plant", "plant/location", "site", "unit", "branch", "location name", "risk location"
    ],
    "currency": [
        "currency", "curr"
    ],
    "accumulated_depreciation": [
        "accumulated depreciation", "accum. dep.", "accum dep", "total dep", "depreciation", "dep. till date", "accum.dep."
    ],
    "book_value": [
        "book value", "book val.", "wdv", "net block", "net value", "carrying value", "written down value", "closing wdv", "start book.val", "start book val", "end book val", "end book.val"
    ],
    "quantity": [
        "quantity", "qty", "count"
    ],
    "vendor": [
        "vendor", "supplier", "manufacturer"
    ],
    "invoice_number": [
        "invoice number", "invoice no", "inv no", "bill no"
    ]
}

def normalize_header(h):
    h = str(h).strip().lower()
    h = re.sub(r'[^a-z0-9]', ' ', h)
    h = re.sub(r'\s+', ' ', h)
    return h

def is_financial_column(header):
    norm = normalize_header(header)
    return any(kw in norm for kw in ["wdv", "netblock", "bookvalue", "accumulateddepreciation", "depreciation"])


def excel_serial_to_year(value):
    if pd.isna(value) or value == "":
        return None

    if isinstance(value, (int, float)):
        # 4-digit year
        if 1950 <= value <= 2026:
            return int(value)
        # 2-digit year
        if 30 <= value <= 99:
            return 1900 + int(value)
        if 0 <= value <= 29:
            return 2000 + int(value)
        # Excel serial
        if value > 10000:
            # Excel base date is 1899-12-30
            dt = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=int(value))
            if 1950 <= dt.year <= 2026:
                return dt.year
        return None

    s = str(value).strip()
    if not s:
        return None

    match4 = re.search(r'(19|20)\d{2}', s)
    if match4:
        return int(match4.group(0))

    match2 = re.search(r'(?:FY)?\s*(\d{2})[-/](\d{2})', s, re.IGNORECASE)
    if match2:
        y = int(match2.group(1))
        return 2000 + y if y <= 30 else 1900 + y

    try:
        parsed = pd.to_datetime(s)
        if 1950 <= parsed.year <= 2026:
            return parsed.year
    except:
        pass

    return None

def excel_serial_to_datetime(value):
    if pd.isna(value) or value == "":
        return ""
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value
    if isinstance(value, (int, float)) and value > 10000:
        return (datetime.datetime(1899, 12, 30) + datetime.timedelta(days=int(value))).date()
    try:
        parsed = pd.to_datetime(str(value).strip())
        return parsed.date()
    except:
        return value

def to_number(v):
    if pd.isna(v) or v == "":
        return 0
    if isinstance(v, (int, float)):
        return float(v)

    cleaned = re.sub(r'[,₹$\s]', '', str(v))
    try:
        return float(cleaned)
    except:
        return 0

def get_wpi_value(wpi_cat, year, stage):
    if not wpi_cat or pd.isna(year):
        return None
    year_str = str(int(year))

    if WPI_DATA is not None and stage in WPI_DATA and year_str in WPI_DATA[stage].columns:
        # Case insensitive match for index
        index_lower = WPI_DATA[stage].index.str.lower()
        wpi_cat_lower = str(wpi_cat).lower()
        if wpi_cat_lower in index_lower:
            # Find the actual original casing
            actual_cat = WPI_DATA[stage].index[index_lower == wpi_cat_lower][0]
            val = WPI_DATA[stage].loc[actual_cat, year_str]
            if pd.notna(val) and val != "":
                return float(val)
    return None

from google import genai
from google.genai import types

CATEGORY_CACHE = {}
CATEGORY_CACHE_FILE = os.path.join(DATA_DIR, "category_cache.json")

def load_category_cache():
    global CATEGORY_CACHE
    if os.path.exists(CATEGORY_CACHE_FILE):
        try:
            with open(CATEGORY_CACHE_FILE, 'r', encoding='utf-8') as f:
                raw_cache = json.load(f)
                CATEGORY_CACHE = {
                    k: v for k, v in raw_cache.items()
                    if v and not str(v).lower().startswith("pending")
                    and not "error" in str(v).lower()
                    and not "quota" in str(v).lower()
                }
        except Exception as e:
            logger.error(f"Error loading category cache: {e}")
            CATEGORY_CACHE = {}

def save_category_cache():
    try:
        clean_cache = {
            k: v for k, v in CATEGORY_CACHE.items()
            if v and not str(v).lower().startswith("pending")
            and not "error" in str(v).lower()
            and not "quota" in str(v).lower()
        }
        with open(CATEGORY_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(clean_cache, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving category cache: {e}")

load_category_cache()

def get_applicable_stages(cap_year):
    if cap_year is None:
        return STAGES_ORDERED
    applicable_stages = []
    for s in STAGES_ORDERED:
        if STAGE_END_YEAR[s] >= cap_year:
            applicable_stages.append(s)
    return applicable_stages

import json

LAST_RUN_GEMINI_CALLS = 0

def batch_classify_categories_with_gemini(descriptions, valid_categories_raw, valid_categories_formatted):
    global LAST_RUN_GEMINI_CALLS
    # Filter descriptions that are not in cache
    uncached_descriptions = [str(d).lower().strip() for d in descriptions if str(d).lower().strip() not in CATEGORY_CACHE and str(d).strip() != ""]
    # Remove duplicates
    uncached_descriptions = list(set(uncached_descriptions))
    
    if not uncached_descriptions:
        return
        
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        logger.error("[WPI ERROR] GEMINI_API_KEY not found.")
        for d in uncached_descriptions:
            CATEGORY_CACHE[d] = "NO_MATCH"
        return
        
    client = genai.Client(api_key=gemini_key)
    model_name = os.getenv("GEMINI_MODEL")
    
    batch_size = 100
    for i in range(0, len(uncached_descriptions), batch_size):
        batch = uncached_descriptions[i:i+batch_size]
        
        prompt = (
            f"From the WPI category list below, choose the SINGLE best-matching category for each of the provided asset descriptions. "
            f"You do NOT need a perfect or exact match — if a specific sub-category doesn't fit well, choose the closest BROAD GROUP category instead (rows tagged 'Broad Group' in the Tier column exist specifically for this purpose). "
            f"Return ONLY a JSON object mapping the exact description string to the matched category string (without the Tier suffix). "
            f"Do not paraphrase or reword the category name itself. "
            f"Return 'NO_MATCH' only if the asset is genuinely unrelated to every category in the list, not merely because no category is a perfect fit.\n\n"
            f"Categories:\n" + "\n".join(valid_categories_formatted) + "\n\n"
            f"Descriptions:\n" + "\n".join(batch)
        )
        
        max_retries = 3
        backoff = 1
        
        for attempt in range(1, max_retries + 1):
            try:
                LAST_RUN_GEMINI_CALLS += 1
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json"
                    )
                )
                raw_text = getattr(response, "text", None)
                if not raw_text:
                    try:
                        raw_text = response.candidates[0].content.parts[0].text
                    except Exception:
                        raw_text = "{}"
                
                result_text = str(raw_text).strip()
                if result_text.startswith("```json"):
                    result_text = result_text[7:]
                if result_text.startswith("```"):
                    result_text = result_text[3:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                
                try:
                    mapped_results = json.loads(result_text)
                    for desc, cat in mapped_results.items():
                        desc_key = str(desc).lower().strip()
                        if cat in valid_categories_raw:
                            CATEGORY_CACHE[desc_key] = cat
                        else:
                            CATEGORY_CACHE[desc_key] = "NO_MATCH"
                            
                    # Fill any missing from batch
                    for d in batch:
                        if d not in CATEGORY_CACHE:
                            CATEGORY_CACHE[d] = "NO_MATCH"
                    break # Success, break retry loop
                except json.JSONDecodeError:
                    logger.warning("[GEMINI] JSON Decode Error on batch. Retrying...")
                    if attempt == max_retries:
                        for d in batch:
                            CATEGORY_CACHE[d] = "NO_MATCH"
                    
            except Exception as e:
                error_msg = str(e).lower()
                is_quota_error = "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg or "resource_exhausted" in error_msg or "503" in error_msg or "unavailable" in error_msg or "high demand" in error_msg
                if is_quota_error:
                    logger.warning("[GEMINI] Rate limit hit. Sleeping for 20 seconds before retry...")
                    time.sleep(20)
                    if attempt == max_retries:
                        logger.error("[GEMINI] Repeated rate limits. Aborting remaining items without caching errors.")
                        return
                
                if attempt < max_retries and not is_quota_error:
                    time.sleep(backoff)
                    backoff *= 2
                elif not is_quota_error:
                    for d in batch:
                        CATEGORY_CACHE[d] = "NO_MATCH"
        
        # Avoid hitting 15 RPM limits by resting between successful batches
        time.sleep(2)

    
    # Save the updated cache to disk
    save_category_cache()

def calculateWPIReplacementValue(wpi_cat, acquisition_value, cap_year):
    if cap_year > REFERENCE_YEAR:
        return acquisition_value, "Success", "N/A (Future Purchase)", None, None

    # Filter to stages that have data for this category
    stages_with_data = [s for s in STAGES_ORDERED if s in WPI_DATA and wpi_cat in WPI_DATA[s].index]
    if not stages_with_data:
        return acquisition_value, "Success", f"No WPI series data for {wpi_cat} - held at cost", None, None

    if "computer" in str(wpi_cat).lower():
        # Enforce Computer Exception
        allowed_stages = ["1994-95", "2004-05", "2011-12"]
        stages_with_data = [s for s in stages_with_data if s in allowed_stages]

    applicable_stages = get_applicable_stages(cap_year)
    chain_stages = [s for s in applicable_stages if s in stages_with_data]

    if not chain_stages:
        # cap_year is earlier than earliest stage with data -> start at first stage that has data
        earliest_stage_idx = STAGES_ORDERED.index(stages_with_data[0])
        chain_stages = [s for s in STAGES_ORDERED[earliest_stage_idx:] if s in stages_with_data]

    carryForward = float(acquisition_value)
    isFirstStage = True
    firstWpiStart = None
    lastWpiEnd = None

    for stage in chain_stages:
        if isFirstStage:
            if cap_year >= STAGE_START_YEAR.get(stage, 1961):
                wpiStart = get_wpi_value(wpi_cat, cap_year, stage)
            else:
                # Started at first stage with data, asset purchased prior to stage start
                wpiStart = get_wpi_value(wpi_cat, STAGE_START_YEAR.get(stage, 1961), stage) or 100.0
            firstWpiStart = wpiStart
            isFirstStage = False
        else:
            wpiStart = 100.0

        wpiEnd = get_wpi_value(wpi_cat, STAGE_END_YEAR[stage], stage)
        lastWpiEnd = wpiEnd

        if wpiStart is None or wpiEnd is None:
            return acquisition_value, "Success", f"Missing WPI data for category in stage {stage} - held at cost", None, None

        inflationPct = max(0.0, (wpiEnd - wpiStart) / wpiStart)
        carryForward = carryForward * (1 + inflationPct)

    return carryForward, "Success", "Multi-stage chain-linking", firstWpiStart, lastWpiEnd

def process_file(file_path, wpi_group, user_mapping_dict=None, header_row_idx=0, best_sheet=None, progress_callback=None, export_to_disk=False):
    global WPI_DATA, LAST_RUN_GEMINI_CALLS
    LAST_RUN_GEMINI_CALLS = 0
    if not WPI_DATA:
        load_datasets()
    load_category_synonyms()
    t_start = time.time()

    if progress_callback:
        progress_callback(5, "Opening Excel file and analyzing sheets...")

    t0 = time.time()
    
    xl = None
    try:
        xl = pd.ExcelFile(file_path)

        if not best_sheet and xl.sheet_names:
            best_sheet = xl.sheet_names[0]

        # Header row detection logic if not provided by user mapping
        if not user_mapping_dict:
            df_head = xl.parse(best_sheet, header=None, nrows=35)
            best_header_idx = -1
            max_score = -1
            
            for i in range(len(df_head)):
                row = df_head.iloc[i].fillna("").astype(str).tolist()
                score = sum(1 for cell in row if cell.strip() != "" and not cell.strip().replace(".", "", 1).isdigit())
                if score > max_score:
                    max_score = score
                    best_header_idx = i

            if best_header_idx == -1:
                best_header_idx = 0
            header_row_idx = best_header_idx

        # Read the headers from the specified header row
        df_head = xl.parse(best_sheet, header=None, skiprows=header_row_idx, nrows=1)
        headers = df_head.iloc[0].fillna("").astype(str).tolist()

        best_map = {}
        
        frontend_keys = {
            "assetCode": "asset_code",
            "description": "asset_description",
            "capDate": "purchase_date",
            "acquisitionValue": "acquisition_value",
            "accumDep": "accumulated_depreciation",
            "bookValue": "book_value",
            "currency": "currency",
            "location": "location",
            "majorCategory": "major_category",
            "assetClass": "asset_class",
            "subCategory": "sub_category"
        }
        
        backend_keys = {
            "assetCode": "asset_code",
            "description": "asset_description",
            "capDate": "capitalized_date",
            "acquisitionValue": "acquisition_value",
            "accumDep": "accumulated_depreciation",
            "bookValue": "book_value",
            "currency": "currency",
            "location": "location",
            "majorCategory": "major_category",
            "assetClass": "asset_class",
            "subCategory": "sub_category"
        }
        
        if user_mapping_dict and len(user_mapping_dict) > 0:
            for camel, f_key in frontend_keys.items():
                col_name = user_mapping_dict.get(f_key)
                if col_name and col_name in headers:
                    best_map[camel] = headers.index(col_name)
                else:
                    best_map[camel] = -1
        else:
            # Auto-detect using the new robust system
            sample_df = xl.parse(best_sheet, skiprows=header_row_idx + 1, nrows=5)
            sample_rows = [row.fillna("").astype(str).tolist() for _, row in sample_df.iterrows()]
            
            detection_results = resolve_columns(headers, sample_rows)
            
            for camel, b_key in backend_keys.items():
                result = detection_results.get("suggestions", {}).get(b_key, {})
                col_name = result.get("mapped_column")
                if col_name and col_name in headers:
                    best_map[camel] = headers.index(col_name)
                else:
                    best_map[camel] = -1

            
        best_header_idx = header_row_idx

        logger.info("--- VALIDATION LOGGING ---")
        logger.info(f"Exact Raw Headers read: {headers}")
        logger.info(f"Column Mapping dict (Internal): {best_map}")
        logger.info("--------------------------")

        t_read_excel = time.time() - t0

        t0 = time.time()
        if progress_callback:
            progress_callback(15, f"Reading data from sheet '{best_sheet}'...")
        # Read actual data
        df = xl.parse(best_sheet, skiprows=best_header_idx)
    finally:
        if xl is not None:
            xl.close()
    # Clean up column headers (trim leading/trailing spaces and multiple spaces)
    df.columns = [" ".join(str(c).split()) for c in df.columns]

    # Standardize Class column to string to prevent mixed types
    if best_map.get('assetClass', -1) != -1:
        class_col = df.columns[best_map['assetClass']]
        df[class_col] = df[class_col].astype(str)

    # Convert capDate from excel serial to datetime
    if best_map.get('capDate', -1) != -1:
        cap_col = df.columns[best_map['capDate']]
        df[cap_col] = df[cap_col].apply(excel_serial_to_datetime)

    t_parse_excel = time.time() - t0

    # User requested debug prints
    logger.info("--- PIPELINE DEBUG: STAGE 1 (After Upload) ---")
    logger.info(f"Rows after upload: {len(df)}")

    acq_col = None
    code_col = None
    if best_map.get('acquisitionValue', -1) != -1:
        acq_col = df.columns[best_map['acquisitionValue']]
        logger.info(f"Acquisition Sum: {pd.to_numeric(df[acq_col], errors='coerce').sum()}")
    else:
        logger.warning("Acquisition Sum: 0 (Column not mapped)")

    if best_map.get('assetCode', -1) != -1:
        code_col = df.columns[best_map['assetCode']]
        logger.info(f"Unique Asset Codes: {df[code_col].nunique()}")
    else:
        logger.info("Unique Asset Codes: 0 (Column not mapped)")

    # Remove completely empty rows
    df = df.dropna(how='all')

    logger.info("--- PIPELINE DEBUG: STAGE 2 (After dropna) ---")
    logger.info(f"Rows: {len(df)}")
    if acq_col is not None:
        logger.info(f"Acquisition Sum: {pd.to_numeric(df[acq_col], errors='coerce').sum()}")

    # Fill NaN with empty string to avoid JSON serialization issues
    df = df.fillna("")

    if progress_callback:
        progress_callback(25, f"Loaded {len(df):,} assets. Classifying categories...")

    logger.info("--- BATCH CLASSIFICATION ---")
    
    # 1. Pre-extract descriptions grouped by most recent stage
    descriptions_by_stage = {}
    for original_idx, row in df.iterrows():
        raw_row = row.tolist()
        def get_temp_val(field):
            idx = best_map.get(field, -1)
            return raw_row[idx] if idx != -1 and idx < len(raw_row) else ""
            
        description = str(get_temp_val("description")).strip()
        desc_lower = description.lower()
        if not description or description.lower() == "nan":
            continue
            
        capDate = get_temp_val("capDate")
        purchaseYear = excel_serial_to_year(capDate)
        
        major_cat = get_temp_val("majorCategory")
        sub_cat = get_temp_val("subCategory")
        asset_class = get_temp_val("assetClass")
        
        norm_major = normalize_text(major_cat)
        norm_sub = normalize_text(sub_cat)
        norm_class = normalize_text(asset_class)
        
        # Priority: Major Category > Sub Category > Asset Class
        norm_cat = norm_major if norm_major else (norm_sub if norm_sub else norm_class)
        
        norm_candidates = [norm_major, norm_sub, norm_class]
        is_row_software = any(bool(re.search(r'\bsoftwares?\b', nc)) for nc in norm_candidates if nc)
        is_row_building = any(bool(re.search(r'\bbuildings?\b', nc)) for nc in norm_candidates if nc)
        is_row_land = any(bool(re.search(r'\blands?\b', nc)) for nc in norm_candidates if nc)

        is_direct_mapped = False
        if is_row_software or is_row_building or is_row_land:
            is_direct_mapped = True
        elif desc_lower in SYNONYM_MAPPING:
            is_direct_mapped = True
        else:
            # Check synonym mapping on categories
            norm_candidates = [norm_major, norm_sub, norm_class]
            for nc in norm_candidates:
                if nc in ("equipment", "office equipments", "miscellaneous", "miscellaneous equipment", "office equipment") or nc.replace(".", "").isdigit():
                    continue
                if nc in SYNONYM_MAPPING:
                    is_direct_mapped = True
                    break
            
            # If still not mapped, check description keywords (whole word only)
            if not is_direct_mapped:
                for kw in DESCRIPTION_KEYWORDS:
                    if re.search(r'\b' + re.escape(kw) + r'\b', desc_lower):
                        is_direct_mapped = True
                        break
        
        if not is_direct_mapped and purchaseYear:
            app_stages = get_applicable_stages(purchaseYear)
            if app_stages:
                most_recent_stage = app_stages[-1]
                if most_recent_stage not in descriptions_by_stage:
                    descriptions_by_stage[most_recent_stage] = set()
                descriptions_by_stage[most_recent_stage].add(desc_lower)
                
    # 2. Call batch classification
    for stage, descs in descriptions_by_stage.items():
        if stage in WPI_DATA:
            df_stage = WPI_DATA[stage]
            
            # List every row whose Tier is not "Broad Group" + All commodities
            valid_cats_raw = VALID_WPI_GROUPS
            valid_cats_formatted = [f"{g}" for g in VALID_WPI_GROUPS]
                
            logger.info(f"Batch classifying {len(descs)} descriptions for stage {stage}...")
            # Sort the set into a list so batch order is stable across runs
            sorted_descs = sorted(list(descs))
            batch_classify_categories_with_gemini(sorted_descs, valid_cats_raw, valid_cats_formatted)

    if progress_callback:
        progress_callback(40, f"Categories matched. Calculating multi-stage replacement values...")

    t0 = time.time()

    # We will format the result similar to the original JS
    results = []
    validation_rows = []
    
    # Preserve original FAR exactly as uploaded
    df_export = df.copy()
    
    # Rename 'Age (Years)' if it exists
    df_export.rename(columns={"Age (Years)": "Asset Age", "Age (years)": "Asset Age"}, inplace=True)
    
    # Initialize calculated columns with default Skipped values using object dtype to allow mixed types
    for col in ["WPI Group", "WPI Series", "Purchase Year WPI", "Current Year WPI", 
                "Calculation Year", "Calculation Method", "Replacement Value", 
                "Difference", "Increase %", "Status"]:
        df_export[col] = "-"
        df_export[col] = df_export[col].astype(object)
        
    df_export["Status"] = "Skipped (Invalid/Footer Row)"

    total_calc_rows = len(df)
    row_calc_counter = 0

    for original_idx, row in df.iterrows():
        row_calc_counter += 1
        if progress_callback and (row_calc_counter % 500 == 0 or row_calc_counter == total_calc_rows):
            pct = int(40 + (row_calc_counter / max(1, total_calc_rows)) * 50)
            progress_callback(pct, f"Calculating replacement values: {row_calc_counter:,} of {total_calc_rows:,} assets...")

        # Get raw row data as a dict or array? The UI expects rawRow to be an array of values
        raw_row = row.tolist()

        # Helper to get mapped value
        def get_val(field):
            idx = best_map.get(field, -1)
            return raw_row[idx] if idx != -1 and idx < len(raw_row) else ""

        capDate = get_val("capDate")
        purchaseYear = excel_serial_to_year(capDate)

        assetCode = str(get_val("assetCode")).strip()
        description = str(get_val("description")).strip()
        
        # Fallback for description if it's completely missing
        if not description or description.lower() == "nan":
            fallback = str(get_val("subCategory")).strip()
            if not fallback or fallback.lower() == "nan":
                fallback = str(get_val("assetClass")).strip()
            
            if fallback and fallback.lower() != "nan":
                description = fallback

        capDateStr = str(capDate).strip()

        acquisitionValueRaw = get_val("acquisitionValue")
        acquisitionValue = to_number(acquisitionValueRaw)

        is_missing_code = not assetCode or assetCode.lower() == "nan"
        is_missing_desc = not description or description.lower() == "nan"
        is_missing_date = not capDateStr or capDateStr.lower() == "nan" or capDateStr == "NaT"

        desc_lower = description.lower()
        is_summary_keyword = "total" in desc_lower or "summary" in desc_lower or "footer" in desc_lower or "grand" in desc_lower

        # A row is considered a summary/footer row if it contains a summary keyword AND has a missing core field (like asset code or date)
        is_footer = is_summary_keyword and (is_missing_code or is_missing_date)

        # BUSINESS RULES: Exclude row
        # We drop if it's explicitly a footer, or if the essential fields (Description or Cap Date) are completely missing.
        if is_footer:
            reason = "Footer/Summary row"
            logger.info(f"DROPPED ROW | RowNum: {original_idx + 2} | AssetCode: {assetCode} | Desc: {description} | AcqValue: {acquisitionValueRaw} | Reason: {reason}")
            continue

        row_obj = {
            "assetCode": assetCode,
            "description": description,
            "capDate": capDate,
            "purchaseYear": purchaseYear,
            "acquisitionValue": acquisitionValue,
            "accumDep": to_number(get_val("accumDep")),
            "bookValue": to_number(get_val("bookValue")),
            "currency": get_val("currency"),
            "assetClass": get_val("assetClass"),
            "location": get_val("location"),
            "majorCategory": get_val("majorCategory"),
            "subCategory": get_val("subCategory"),
            "rawRow": raw_row,
            "_raw": {
                "capDate": capDate,
                "acquisitionValue": acquisitionValueRaw
            }
        }

        # Calculation
        replacementValue = 0
        purchaseWpi = None
        currentWpi = None
        note = None
        status = "Success"
        difference = 0
        calculation_method = ""

        major_cat = get_val("majorCategory")
        sub_cat = get_val("subCategory")
        asset_class = get_val("assetClass")
        
        candidates = [major_cat, sub_cat, asset_class]
        norm_candidates = [normalize_text(c) for c in candidates if normalize_text(c)]

        desc_lower = description.lower()
        # Requirement 2: decide software from category or sub-category, not from words in the description
        is_software = any(bool(re.search(r'\bsoftwares?\b', nc)) for nc in norm_candidates)
        is_land = any(bool(re.search(r'\blands?\b', nc)) for nc in norm_candidates)
        is_building = any(bool(re.search(r'\bbuildings?\b', nc)) for nc in norm_candidates)

        row_wpi_group = None
        tier_status = None
        note_override = None
        resolution_method = "-"

        if is_software:
            row_wpi_group = "Software"
            tier_status = "High Confidence"
            resolution_method = "Category Rule"
        elif is_land:
            row_wpi_group = "Land"
            tier_status = "High Confidence"
            resolution_method = "Category Rule"
        elif is_building:
            row_wpi_group = "Building"
            tier_status = "High Confidence"
            resolution_method = "Category Rule"
        elif is_missing_desc:
            note_override = "Missing Asset Description"
        elif is_missing_date:
            note_override = "Missing Capitalized Date"
        elif purchaseYear:
            is_direct = False
            # Check description exact match on synonyms
            if desc_lower in SYNONYM_MAPPING:
                row_wpi_group = SYNONYM_MAPPING[desc_lower]
                is_direct = True
                tier_status = "High Confidence"
                resolution_method = "Synonym Match"
                
            if not is_direct:
                for norm_cat in norm_candidates:
                    if norm_cat in ("equipment", "miscellaneous", "miscellaneous equipment") or norm_cat.replace(".", "").isdigit():
                        continue
                        
                    if norm_cat in SYNONYM_MAPPING:
                        row_wpi_group = SYNONYM_MAPPING[norm_cat]
                        is_direct = True
                        tier_status = "High Confidence"
                        resolution_method = "Synonym Match"
                        break
                    
                    # Fuzzy Matching for SYNONYM_MAPPING
                    close_matches = difflib.get_close_matches(norm_cat, SYNONYM_MAPPING.keys(), n=1, cutoff=0.85)
                    if close_matches:
                        fuzzy_match = close_matches[0]
                        row_wpi_group = SYNONYM_MAPPING[fuzzy_match]
                        is_direct = True
                        tier_status = "High Confidence (Fuzzy Match)"
                        resolution_method = "Fuzzy Synonym"
                        logger.info(f"Fuzzy Matched Category '{norm_cat}' to '{fuzzy_match}' -> '{row_wpi_group}'")
                        break
                        
            # Check description keywords (whole words)
            if not is_direct:
                for kw, group in DESCRIPTION_KEYWORDS.items():
                    pattern = r'\b' + re.escape(kw) + r'\b'
                    if re.search(pattern, desc_lower):
                        row_wpi_group = group
                        is_direct = True
                        tier_status = "High Confidence (Keyword Match)"
                        resolution_method = "Keyword Match"
                        break

            if not is_direct:
                    app_stages = get_applicable_stages(purchaseYear)
                    if app_stages:
                        most_recent_stage = app_stages[-1]
                    if most_recent_stage in WPI_DATA:
                        gemini_match = CATEGORY_CACHE.get(desc_lower, "NO_MATCH")
                        
                        if gemini_match == "API_QUOTA_ERROR":
                            row_wpi_group = None
                            note_override = "LLM classification failed due to Gemini API Quota Limits"
                        elif gemini_match != "NO_MATCH":
                            if gemini_match not in VALID_WPI_GROUPS:
                                row_wpi_group = None
                                note_override = f"Category '{gemini_match}' is not in the valid master list"
                            else:
                                row_wpi_group = gemini_match
                                resolution_method = "Gemini API"
                                if 'Tier' in WPI_DATA[most_recent_stage].columns:
                                    tier_val = WPI_DATA[most_recent_stage].loc[gemini_match, 'Tier']
                                    if pd.notna(tier_val):
                                        if "Verified" in str(tier_val):
                                            tier_status = "High Confidence"
                                        elif "Candidate" in str(tier_val):
                                            tier_status = "Needs Team Confirmation"
                                        elif "Broad Group" in str(tier_val):
                                            tier_status = "Approximate - Broad Category Used"
                                        else:
                                            tier_status = "High Confidence"
                                    else:
                                        tier_status = "High Confidence"
                                else:
                                    tier_status = "High Confidence" # Fallback if tier missing
                        else:
                            row_wpi_group = None
                            note_override = "NO_MATCH returned by Gemini classification"
                    else:
                        note_override = "NO_MATCH returned by Gemini classification"

        is_building = (row_wpi_group == "Building")
        is_land = (row_wpi_group == "Land")
        is_software = (row_wpi_group == "Software")
        
        if row_wpi_group == "Pending (AI quota)":
            row_obj["wpiGroup"] = "Pending (AI quota)"
        else:
            row_obj["wpiGroup"] = row_wpi_group if row_wpi_group else "All commodities"

        val_purchase_wpi = "-"
        val_current_wpi = "-"
        formula_used = ""

        if not purchaseYear:
            status = "Data Missing" if (is_building or is_land) else "WPI Data Missing"
            note = "No purchase year detected in FAR"
            replacementValue = acquisitionValue
            formula_used = "N/A (Missing Year)"
            calculation_method = "Not Available"
            row_obj["wpiGroup"] = "-"
        elif not acquisitionValue:
            status = "Not Applicable (No Acq Value)"
            note = "No acquisition cost detected"
            replacementValue = 0
            formula_used = "0 (No Acq Value)"
            calculation_method = "Not Available"
        elif purchaseYear and purchaseYear > 2025:
            status = "Not Applicable (Future Purchase)"
            note = f"Asset purchased after 2025; replacement value kept equal to acquisition value"
            replacementValue = acquisitionValue
            formula_used = "N/A (Post-Reference Year)"
            calculation_method = "Not Applicable"
            row_obj["wpiGroup"] = "-"
        elif is_building:
            status = "Success"
            years = max(0, REFERENCE_YEAR - purchaseYear)
            replacementValue = acquisitionValue * ((1 + BUILDING_ESCALATION_RATE) ** years)
            calculation_method = "5% Annual Compound Escalation"
            formula_used = f"{acquisitionValue} * (1 + {BUILDING_ESCALATION_RATE}) ^ {years}"
            note = "Used 5% compound escalation for Building"
            difference = replacementValue - acquisitionValue
            row_obj["wpiGroup"] = "Building"
            
            logger.info(f"CALC LOG | Asset: {assetCode} | Category: Building | Purchase Year: {purchaseYear} | Current Year: {REFERENCE_YEAR} | Method: {calculation_method} | Purchase WPI: - | Current WPI: - | Replacement Value: {replacementValue}")
            
        elif is_land:
            status = "Success"
            years = max(0, REFERENCE_YEAR - purchaseYear)
            replacementValue = acquisitionValue * ((1 + BUILDING_ESCALATION_RATE) ** years)
            calculation_method = "5% Annual Compound Escalation"
            formula_used = f"{acquisitionValue} * (1 + {BUILDING_ESCALATION_RATE}) ^ {years}"
            note = "Used 5% compound escalation for Land"
            difference = replacementValue - acquisitionValue
            row_obj["wpiGroup"] = "Land"
            
            logger.info(f"CALC LOG | Asset: {assetCode} | Category: Land | Purchase Year: {purchaseYear} | Current Year: {REFERENCE_YEAR} | Method: {calculation_method} | Purchase WPI: - | Current WPI: - | Replacement Value: {replacementValue}")
            
        elif is_software:
            status = "Success"
            note = "Software products held at cost (no WPI exists)"
            replacementValue = acquisitionValue
            formula_used = "Held at cost"
            calculation_method = "At Cost (Software)"
            row_obj["wpiGroup"] = "Software"
            difference = 0
            
        elif row_obj["wpiGroup"] == "Pending (AI quota)":
            status = "Success"
            note = note_override if note_override else "Held at cost (AI Quota)"
            replacementValue = acquisitionValue
            formula_used = "Held at cost"
            calculation_method = "At Cost"
            difference = 0
        elif note_override and row_obj["wpiGroup"] == "All commodities":
            calculation_method = "WPI Based"
            replacementValue, fallback_status, formula_used, purchaseWpi, currentWpi = calculateWPIReplacementValue(
                "All commodities", acquisitionValue, purchaseYear
            )
            val_purchase_wpi = purchaseWpi if purchaseWpi is not None else "-"
            val_current_wpi = currentWpi if currentWpi is not None else "-"
            
            if fallback_status != "Success" or "held at cost" in str(formula_used).lower():
                status = "Success"
                note = formula_used
                replacementValue = acquisitionValue
                formula_used = "Held at cost"
                calculation_method = "At Cost"
                difference = 0
            else:
                status = "Success"
                note = note_override
                difference = replacementValue - acquisitionValue
                if purchaseWpi is not None and currentWpi is not None:
                    try:
                        p_val = float(purchaseWpi)
                        c_val = float(currentWpi)
                        if abs(c_val - p_val) < 1e-5:
                            calculation_method = "WPI Based (no index change)"
                        elif c_val < p_val - 1e-5 and difference == 0:
                            calculation_method = "WPI Based (floored at acquisition value)"
                        else:
                            calculation_method = "WPI Based"
                    except (ValueError, TypeError):
                        calculation_method = "WPI Based"
                
        elif row_obj["wpiGroup"] == "-" or row_obj["wpiGroup"] == "Not Applicable":
            status = "Success"
            note = note_override if note_override else "Asset category not subject to automatic WPI indexing"
            replacementValue = acquisitionValue
            formula_used = "Held at cost"
            calculation_method = "At Cost"
            difference = 0
        else:
            calculation_method = "WPI Based"
            replacementValue, status, formula_used, purchaseWpi, currentWpi = calculateWPIReplacementValue(
                row_wpi_group, acquisitionValue, purchaseYear
            )

            val_purchase_wpi = purchaseWpi if purchaseWpi is not None else "-"
            val_current_wpi = currentWpi if currentWpi is not None else "-"

            if status != "Success" or "held at cost" in str(formula_used).lower():
                status = "Success"
                note = formula_used
                replacementValue = acquisitionValue
                formula_used = "Held at cost"
                calculation_method = "At Cost (No Index Data)"
                difference = 0
            else:
                difference = replacementValue - acquisitionValue
                if purchaseWpi is not None and currentWpi is not None:
                    try:
                        p_val = float(purchaseWpi)
                        c_val = float(currentWpi)
                        if abs(c_val - p_val) < 1e-5:
                            calculation_method = "WPI Based (no index change)"
                        elif c_val < p_val - 1e-5 and difference == 0:
                            calculation_method = "WPI Based (floored at acquisition value)"
                        else:
                            calculation_method = "WPI Based"
                    except (ValueError, TypeError):
                        calculation_method = "WPI Based"

                # VALIDATION: Rule 4
                if replacementValue < acquisitionValue:
                    replacementValue = acquisitionValue
                    status = "Success"
                    
        row_obj["ConfidenceStatus"] = tier_status if tier_status else "Success"

        # Reduced verbosity to speed up processing for large FAR files
        # Only print summary metrics at the end, not per-asset logs.
        if calculation_method == "WPI Based" and status == "Success":
            if getattr(process_file, "lookup_counter", 0) < 5:
                logger.info("[WPI LOOKUP]")
                logger.info(f"Group: {row_wpi_group}")
                logger.info(f"Purchase Year: {purchaseYear}")
                logger.info(f"Purchase WPI: {purchaseWpi}")
                logger.info(f"Current Year: {LATEST_WPI_YEAR}")
                logger.info(f"Current WPI: {currentWpi}")
                process_file.lookup_counter = getattr(process_file, "lookup_counter", 0) + 1

        
        display_wpi_group = row_wpi_group

        row_obj["purchaseWpi"] = purchaseWpi
        row_obj["currentWpi"] = currentWpi
        row_obj["replacementValue"] = replacementValue
        row_obj["difference"] = difference
        row_obj["note"] = note
        row_obj["status"] = status
        row_obj["calculationMethod"] = calculation_method
        row_obj["resolutionMethod"] = resolution_method
        if display_wpi_group:
            row_obj["wpiGroup"] = display_wpi_group

        results.append(row_obj)

        # Populate export columns exactly matching original row index
        is_calc_success = status == "Success" or is_building or is_land or (status == "Not Applicable") or ("WPI Based" in str(calculation_method))
        increase_percentage = (difference / acquisitionValue) if (acquisitionValue and difference is not None and difference != 0) else (0 if is_calc_success else "-")
        
        # Override Not Applicable WPI fields
        p_wpi = purchaseWpi if purchaseWpi is not None else "-"
        c_wpi = currentWpi if currentWpi is not None else "-"
        
        df_export.at[original_idx, "WPI Group"] = row_obj.get("wpiGroup", "-")
        df_export.at[original_idx, "WPI Series"] = LATEST_SERIES if calculation_method == "WPI Based" else "-"
        df_export.at[original_idx, "Purchase Year WPI"] = p_wpi
        df_export.at[original_idx, "Current Year WPI"] = c_wpi
        df_export.at[original_idx, "Calculation Year"] = LATEST_WPI_YEAR
        df_export.at[original_idx, "Calculation Method"] = calculation_method
        df_export.at[original_idx, "Replacement Value"] = replacementValue
        df_export.at[original_idx, "Difference"] = difference
        df_export.at[original_idx, "Increase %"] = increase_percentage
        df_export.at[original_idx, "Status"] = status

        # Build validation row
        validation_rows.append({
            "Asset Code": assetCode,
            "Asset Description": description,
            "Major Category": get_val("majorCategory"),
            "Sub Category": get_val("subCategory"),
            "Purchase Date": capDate,
            "Purchase Year": purchaseYear,
            "WPI Category": row_obj.get("wpiGroup", ""),
            "Purchase WPI": val_purchase_wpi,
            "Current Year": LATEST_WPI_YEAR if currentWpi else "",
            "Current WPI": val_current_wpi,
            "Acquisition Value": acquisitionValue,
            "Replacement Value": replacementValue,
            "Calculation Method": calculation_method,
            "Formula Used": formula_used,
            "Status": status,
            "Confidence Status": row_obj.get("ConfidenceStatus", "-"),
            "Resolution Method": resolution_method,
            "Note": note
        })

    t_calc_loop = time.time() - t0

    if progress_callback:
        progress_callback(92, "Generating Excel report and reconciled summary sheets...")

    t0 = time.time()
    # Export validation report with unique timestamp
    if export_to_disk and validation_rows:
        import uuid
        unique_suffix = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        val_filename = os.path.join(DOWNLOADS_DIR, f"WPI_Validation_Report_{unique_suffix}.xlsx")
        pd.DataFrame(validation_rows).to_excel(val_filename, index=False)
        # Also maintain latest copy in downloads for reference without polluting root
        pd.DataFrame(validation_rows).to_excel("WPI_Validation_Report.xlsx", index=False)
        logger.info(f"--- Saved {val_filename} ---")
        
        # Export Broad Group Assets
        broad_group_assets = [r for r in validation_rows if r["Confidence Status"] == "Approximate - Broad Category Used"]
        if broad_group_assets:
            broad_filename = os.path.join(DOWNLOADS_DIR, f"WPI_Broad_Group_Assets_{unique_suffix}.xlsx")
            pd.DataFrame(broad_group_assets).to_excel(broad_filename, index=False)
            logger.info(f"--- Saved {broad_filename} ---")

    # Calculate Dashboard Metrics
    metrics = {
        "Total Assets": 0,
        "Calculated Assets": 0,
        "Manual Review Count": 0,
        "Total Acquisition Value": 0,
        "Total Accumulated Depreciation": 0,
        "Total Book Value": 0,
        "Total Replacement Value": 0,
        "Assets by Major Category": {},
        "Assets by Sub Category": {},
        "Assets by Plant/Location": {},
        "Manual Review Breakdown": {},
        "Broad Group Asset Count": 0,
        "Calculation Bugs Count": 0
    }

    if results:
        res_df = pd.DataFrame(results)

        # Total Assets: all rows
        metrics["Total Assets"] = len(res_df)

        # Calculated Assets: all assets with calculated replacement value (including building, land, WPI, etc.)
        def is_calculated_asset(row):
            status = str(row.get("status", "")).strip()
            method = str(row.get("calculationMethod", "")).strip()
            rep = row.get("replacementValue")
            if status == "Success" or "Compound" in method or "WPI" in method or "Escalation" in method or "At Cost" in method:
                return True
            try:
                if rep is not None and str(rep).strip() not in ("-", "", "None") and float(rep) > 0:
                    return True
            except (ValueError, TypeError):
                pass
            return False

        calculated_mask = res_df.apply(is_calculated_asset, axis=1)
        metrics["Calculated Assets"] = int(calculated_mask.sum())

        # Manual Review Count
        manual_review_mask = (
            (res_df['status'] == 'Manual Review Required') |
            res_df['status'].astype(str).str.contains('Manual', case=False, na=False) |
            res_df['status'].astype(str).str.contains('Failed', case=False, na=False) |
            (res_df['status'] == 'Needs Mapping')
        )
        metrics["Manual Review Count"] = int(manual_review_mask.sum())

        metrics["Assets by WPI Category"] = res_df.groupby("wpiGroup").size().to_dict()
        
        # Validation Metrics
        manual_review_df = res_df[manual_review_mask]
        metrics["Manual Review Breakdown"] = manual_review_df.groupby("note").size().to_dict()
        metrics["Broad Group Asset Count"] = int((res_df['ConfidenceStatus'] == 'Approximate - Broad Category Used').sum())
        metrics["Calculation Bugs Count"] = int((res_df['note'] == 'Bug detected: Replacement Value is less than Acquisition Value.').sum())

        # Financial sums on res_df (no total rows)
        metrics["Total Acquisition Value"] = float(res_df["acquisitionValue"].sum())
        metrics["Total Accumulated Depreciation"] = float(res_df["accumDep"].sum())
        metrics["Total Book Value"] = float(res_df["bookValue"].sum())
        metrics["Total Replacement Value"] = float(res_df["replacementValue"].sum())

        major_cat = res_df[res_df["majorCategory"].astype(str).str.strip() != ""]
        metrics["Assets by Major Category"] = major_cat.groupby("majorCategory").size().to_dict()

        sub_cat = res_df[res_df["subCategory"].astype(str).str.strip() != ""]
        metrics["Assets by Sub Category"] = sub_cat.groupby("subCategory").size().to_dict()

        loc_cat = res_df[res_df["location"].astype(str).str.strip() != ""]
        metrics["Assets by Plant/Location"] = loc_cat.groupby("location").size().to_dict()
        metrics["gemini_calls"] = LAST_RUN_GEMINI_CALLS

        logger.info("--- PIPELINE DEBUG: STAGE 3 (API Return) ---")
        logger.info(f"Rows returned by API: {len(results)}")
        logger.info(f"Acquisition Sum: {metrics['Total Acquisition Value']}")
        logger.info("------------------------------------------")

    # Verify we have data to export
    if export_to_disk and not df_export.empty:
        import uuid
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:6]
        download_filename = f"FAR_Replacement_Report_{date_str}_{unique_id}.xlsx"
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        download_path = os.path.join(DOWNLOADS_DIR, download_filename)

        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils.dataframe import dataframe_to_rows

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Processed FAR"
            
            # Write to openpyxl
            for r in dataframe_to_rows(df_export, index=False, header=True):
                ws.append(r)
                
            # Formatting
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill("solid", fgColor="4F81BD")
            align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
            align_left_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)
            
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = align_center

            # Map column names to their letters for dynamic formatting
            col_name_to_letter = {}
            for idx, col_name in enumerate(df_export.columns):
                col_name_to_letter[col_name] = openpyxl.utils.get_column_letter(idx + 1)

            # Set widths dynamically based on column names
            for col_name, letter in col_name_to_letter.items():
                if col_name in ["Replacement Value", "Difference"]:
                    ws.column_dimensions[letter].width = 20
                elif col_name in ["WPI Group", "Calculation Method", "Status"]:
                    ws.column_dimensions[letter].width = 25
                elif col_name in ["Purchase Year WPI", "Current Year WPI"]:
                    ws.column_dimensions[letter].width = 18
                elif col_name in ["Increase %"]:
                    ws.column_dimensions[letter].width = 15
                else:
                    ws.column_dimensions[letter].width = 15 # default fallback for original columns
                    
                # Description usually needs more space, let's try to identify it roughly
                if "desc" in str(col_name).lower():
                    ws.column_dimensions[letter].width = 35

            # Number formatting and alignment
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                for idx, cell in enumerate(row):
                    col_letter = openpyxl.utils.get_column_letter(idx + 1)
                    col_name = df_export.columns[idx]
                    
                    if "desc" in str(col_name).lower():
                        cell.alignment = align_left_wrap
                    else:
                        cell.alignment = align_center
                        
                    # Currencies: Original Acq Value (varies), Replacement Value, Difference
                    is_acq_col = acq_col is not None and col_name == acq_col
                    if is_acq_col or col_name in ['Replacement Value', 'Difference']:
                        if isinstance(cell.value, (int, float)):
                            cell.number_format = r'[>=100000]₹##\,##\,##0.00;[>=1000]₹##\,##0.00;₹##0.00'
                    # Increase %
                    elif col_name == 'Increase %':
                        if isinstance(cell.value, (int, float)):
                            cell.number_format = '0.00%'
                    # WPI
                    elif col_name in ['Purchase Year WPI', 'Current Year WPI']:
                        if isinstance(cell.value, (int, float)):
                            cell.number_format = '0.000000'
                            
                    # Dates (Strip out time 0:00:00)
                    if isinstance(cell.value, (datetime.date, datetime.datetime)):
                        cell.number_format = 'yyyy-mm-dd'

            # Freeze Panes (Header row)
            ws.freeze_panes = "A2"
            
            # AutoFilter
            ws.auto_filter.ref = ws.dimensions

            # Create Summary Sheet
            ws_sum = wb.create_sheet("Summary")
            na_count = int(res_df['status'].astype(str).str.contains('Not Applicable', case=False, na=False).sum())
            summary_rows = [
                ["Metric", "Value"],
                ["Total Assets", metrics["Total Assets"]],
                ["Calculated Assets", metrics["Calculated Assets"]],
                ["Manual Review Count", metrics["Manual Review Count"]],
                ["Not Applicable Count", na_count],
                ["Total Acquisition Value", metrics["Total Acquisition Value"]],
                ["Total Replacement Value", metrics["Total Replacement Value"]],
                ["Total Difference", metrics["Total Replacement Value"] - metrics["Total Acquisition Value"]],
                ["Overall Increase %", ((metrics["Total Replacement Value"] - metrics["Total Acquisition Value"]) / metrics["Total Acquisition Value"]) if metrics["Total Acquisition Value"] else 0],
                ["Calculation Year", LATEST_WPI_YEAR],
                ["Methodology Note", "Replacement values calculated using the approved WPI/special-category methodologies with reference year 2025."]
            ]
            
            summary_rows.append(["", ""])
            summary_rows.append(["WPI Category", "Count of Assets"])
            for wpi_cat, count in metrics.get("Assets by WPI Category", {}).items():
                summary_rows.append([wpi_cat, count])

            for r_idx, r_data in enumerate(summary_rows, 1):
                ws_sum.cell(row=r_idx, column=1, value=r_data[0])
                if len(r_data) > 1:
                    cell = ws_sum.cell(row=r_idx, column=2, value=r_data[1])
                    if r_data[0] in ["Total Acquisition Value", "Total Replacement Value", "Total Difference"]:
                        cell.number_format = r'[>=100000]₹##\,##\,##0.00;[>=1000]₹##\,##0.00;₹##0.00'
                    elif r_data[0] == "Overall Increase %":
                        cell.number_format = '0.00%'
                        
                if r_idx == 1 or r_data[0] == "WPI Category":
                    ws_sum.cell(row=r_idx, column=1).font = Font(bold=True)
                    if len(r_data) > 1:
                        ws_sum.cell(row=r_idx, column=2).font = Font(bold=True)

            ws_sum.column_dimensions['A'].width = 30
            ws_sum.column_dimensions['B'].width = 35

            wb.save(download_path)
            wb.close()

        except Exception as e:
            # Fallback for pandas ExcelWriter if openpyxl fails for some reason
            logger.warning(f"openpyxl formatting failed ({e}), falling back to pandas ExcelWriter.")
            with pd.ExcelWriter(download_path, engine='openpyxl') as writer:
                df_export.to_excel(writer, sheet_name="Processed FAR", index=False)

                # Summary Sheet
                summary_data = {
                    "Metric": [
                        "Total Assets",
                        "Calculated Assets",
                        "Manual Review Count",
                        "Not Applicable Count",
                        "Total Acquisition Value",
                        "Total Replacement Value",
                        "Total Difference",
                        "Overall Increase %",
                        "Calculation Year",
                        "Methodology Note"
                    ],
                    "Value": [
                        metrics["Total Assets"],
                        metrics["Calculated Assets"],
                        metrics["Manual Review Count"],
                        na_count,
                        metrics["Total Acquisition Value"],
                        metrics["Total Replacement Value"],
                        metrics["Total Replacement Value"] - metrics["Total Acquisition Value"],
                        ((metrics["Total Replacement Value"] - metrics["Total Acquisition Value"]) / metrics["Total Acquisition Value"]) if metrics["Total Acquisition Value"] else 0,
                        LATEST_WPI_YEAR,
                        "Replacement values calculated using the approved WPI/special-category methodologies with reference year 2025."
                    ]
                }
                
                # Append WPI categories
                summary_data["Metric"].append("")
                summary_data["Value"].append("")
                summary_data["Metric"].append("WPI Category")
                summary_data["Value"].append("Count of Assets")
                for wpi_cat, count in metrics.get("Assets by WPI Category", {}).items():
                    summary_data["Metric"].append(wpi_cat)
                    summary_data["Value"].append(count)

                pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
        metrics["downloadUrl"] = f"/downloads/{download_filename}"

    def sanitize_for_json(obj):
        if isinstance(obj, dict):
            return {k: sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_for_json(v) for v in obj]
        elif isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        else:
            try:
                if pd.isna(obj) or (isinstance(obj, float) and obj != obj):
                    return None
            except Exception:
                pass
            return obj

    final_result = {
        "headers": df.columns.astype(str).tolist(),
        "columnMapping": best_map,
        "mappedData": results,
        "metrics": metrics
    }

    if progress_callback:
        progress_callback(100, "Calculation completed successfully.")

    return sanitize_for_json(final_result)
