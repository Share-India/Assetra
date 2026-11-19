import re
import pandas as pd
import json
import os

SUFFIX_CACHE_FILE = os.path.join(os.path.dirname(__file__), "data", "suffix_cache.json")

def load_suffix_cache():
    if os.path.exists(SUFFIX_CACHE_FILE):
        try:
            with open(SUFFIX_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_suffix_cache(cache):
    os.makedirs(os.path.dirname(SUFFIX_CACHE_FILE), exist_ok=True)
    with open(SUFFIX_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=4)

def is_mixed_type_column(col_data):
    """
    Checks if a column is a mix of pure numbers and numbers with a short alphabetic suffix.
    E.g., 3100 and "3100R"
    """
    if not col_data: return False
    
    has_number = False
    has_suffixed = False
    
    # regex: starts with digits, optionally ends with 1-3 letters
    pattern = re.compile(r'^(\d+)([a-zA-Z]{1,3})?$')
    
    for val in col_data:
        val_str = str(val).strip()
        if pd.isna(val) or val_str == "":
            continue
            
        match = pattern.match(val_str)
        if match:
            digits = match.group(1)
            suffix = match.group(2)
            
            if suffix:
                has_suffixed = True
            else:
                has_number = True
        else:
            # If any value doesn't match the pattern at all (e.g. pure string like "Computer"), it's not our mixed type
            return False
            
    return has_number and has_suffixed

def process_mixed_type_columns(df):
    """
    Splits any mixed-type column into base numeric and suffix columns.
    Returns the updated df and a list of logs.
    """
    logs = []
    
    # Iterate through a copy of columns since we might add/remove
    for col in list(df.columns):
        sample = df[col].dropna().head(100).tolist()
        if is_mixed_type_column(sample):
            logs.append(f"Mixed-type pattern detected in column '{col}'")
            
            # Split the column
            base_col_name = f"{col}_base_code"
            suffix_col_name = f"{col}_suffix_flag"
            
            base_vals = []
            suffix_vals = []
            
            pattern = re.compile(r'^(\d+)([a-zA-Z]{1,3})?$')
            
            for val in df[col]:
                val_str = str(val).strip()
                if pd.isna(val) or val_str == "":
                    base_vals.append(pd.NA)
                    suffix_vals.append("")
                    continue
                    
                match = pattern.match(val_str)
                if match:
                    base_vals.append(match.group(1)) # The numeric part
                    suffix = match.group(2)
                    suffix_vals.append(suffix.upper() if suffix else "")
                else:
                    base_vals.append(val)
                    suffix_vals.append("")
            
            # Insert the new columns next to the old one
            col_idx = df.columns.get_loc(col)
            df.insert(col_idx + 1, base_col_name, base_vals)
            df.insert(col_idx + 2, suffix_col_name, suffix_vals)
            
            # Optionally we could drop the original col, but we keep it and just re-map the WPI lookup to use base_col_name
            # Wait, if we keep the original col, downstream might still use it if it's named 'Asset Class'.
            # We should probably overwrite the original col with the base code!
            # And keep the suffix as a new column. That way downstream logic (like DIRECT_MAPPING) only sees "3100" and not "3100R".
            df[col] = base_vals
            
            logs.append(f"Successfully split '{col}' into clean numeric field and '{suffix_col_name}'")
            
    return df, logs
