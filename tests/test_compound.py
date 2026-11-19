import sys, os, pandas as pd
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
import calculator

test_cases = [
    {'test': 'TEST 1', 'acq': 100, 'py': 1968, 'cy': 1969},
    {'test': 'TEST 2', 'acq': 100, 'py': 1968, 'cy': 1970},
    {'test': 'TEST 3', 'acq': 100, 'py': 1968, 'cy': 1971},
    {'test': 'TEST 4', 'acq': 2459106, 'py': 1968, 'cy': 2025},
    {'test': 'TEST 5', 'acq': 2459106, 'py': 2025, 'cy': 2025},
]

print('--- Test Results ---')
for tc in test_cases:
    calculator.LATEST_WPI_YEAR = tc['cy']
    years = max(0, calculator.LATEST_WPI_YEAR - tc['py'])
    rep_val = tc['acq'] * ((1 + calculator.BUILDING_ESCALATION_RATE) ** years)
    print(f"{tc['test']}: Acquisition = {tc['acq']}, PY = {tc['py']}, CY = {tc['cy']} -> Calculated Replacement Value: {rep_val:.2f}")
