import sys, os, pandas as pd
filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'WPI_MASTER_DATASET_CATEGORYWISE_v6.xlsx'))
if os.path.exists(filepath):
    xl = pd.ExcelFile(filepath)
    print("Base year sheets with trends:")
    for s in xl.sheet_names:
        if 'base' in s.lower():
            print(f" - {s}")
