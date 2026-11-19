import sys, os, pandas as pd
filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'WPI_MASTER_DATASET_CATEGORYWISE_v6.xlsx'))
if os.path.exists(filepath):
    xl = pd.ExcelFile(filepath)
    for sheet in xl.sheet_names:
        if 'base' in sheet.lower():
            df = pd.read_excel(xl, sheet_name=sheet)
            if 'Category' in df.columns:
                comps = [c for c in df['Category'] if 'comput' in str(c).lower()]
                print(f"Sheet: {sheet} -> {len(comps)} computer categories found.")
