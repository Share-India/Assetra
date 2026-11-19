import sys, os, pandas as pd
filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'WPI_MASTER_DATASET_CATEGORYWISE_v6.xlsx'))
if os.path.exists(filepath):
    xl = pd.ExcelFile(filepath)
    df = pd.read_excel(xl, sheet_name='2011-12 base (current)')
    print(f"Total categories in 2011-12 base: {len(df)}")
