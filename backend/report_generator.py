import io
import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

LATEST_WPI_YEAR = 2025

def generate_excel_report_stream(analysis, rows) -> io.BytesIO:
    """
    Builds the exact Excel report ON-DEMAND in-memory from database rows.
    Zero disk storage required.
    """
    wb = openpyxl.Workbook()
    
    # -------------------------------------------------------------
    # SHEET 1: Processed FAR
    # -------------------------------------------------------------
    ws = wb.active
    ws.title = "Processed FAR"

    columns_order = analysis.columns_order or []
    computed_headers = [
        "WPI Group",
        "WPI Series",
        "Purchase Year WPI",
        "Current Year WPI",
        "Calculation Year",
        "Calculation Method",
        "Replacement Value",
        "Difference",
        "Increase %",
        "Status"
    ]
    all_headers = list(columns_order) + computed_headers
    ws.append(all_headers)

    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center

    # Map column names to column letters
    col_name_to_letter = {}
    for idx, col_name in enumerate(all_headers):
        col_name_to_letter[col_name] = get_column_letter(idx + 1)

    # Set column widths
    for col_name, letter in col_name_to_letter.items():
        if col_name in ["Replacement Value", "Difference"]:
            ws.column_dimensions[letter].width = 20
        elif col_name in ["WPI Group", "Calculation Method", "Status"]:
            ws.column_dimensions[letter].width = 25
        elif col_name in ["Purchase Year WPI", "Current Year WPI"]:
            ws.column_dimensions[letter].width = 18
        elif col_name in ["Increase %"]:
            ws.column_dimensions[letter].width = 15
        elif "desc" in str(col_name).lower():
            ws.column_dimensions[letter].width = 35
        else:
            ws.column_dimensions[letter].width = 15

    # Append rows
    wpi_category_counts = {}
    for row in rows:
        orig = row.original_row if isinstance(row.original_row, dict) else {}
        row_values = [orig.get(col, "") for col in columns_order]

        # WPI category count
        group_val = row.wpi_group or "-"
        wpi_category_counts[group_val] = wpi_category_counts.get(group_val, 0) + 1

        # Format computed fields
        p_wpi = float(row.purchase_wpi) if row.purchase_wpi is not None else "-"
        c_wpi = float(row.current_wpi) if row.current_wpi is not None else "-"
        rep_val = float(row.replacement_value) if row.replacement_value is not None else 0.0
        diff_val = float(row.difference) if row.difference is not None else 0.0
        
        inc_pct = "-"
        if row.increase_pct is not None:
            inc_pct = float(row.increase_pct)
        elif row.status in ["Success", "Not Applicable"]:
            inc_pct = 0.0

        computed_values = [
            group_val,
            row.wpi_series or ("SERIES_2011-12" if row.calculation_method == "WPI Based" else "-"),
            p_wpi,
            c_wpi,
            LATEST_WPI_YEAR,
            row.calculation_method or "-",
            rep_val,
            diff_val,
            inc_pct,
            row.status or "-"
        ]
        ws.append(row_values + computed_values)

    # Apply cell formatting and alignment to data rows
    for r_idx, excel_row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
        for c_idx, cell in enumerate(excel_row):
            col_name = all_headers[c_idx]
            if "desc" in str(col_name).lower():
                cell.alignment = align_left_wrap
            else:
                cell.alignment = align_center

            # Format currencies
            if col_name in ['Replacement Value', 'Difference']:
                if isinstance(cell.value, (int, float)):
                    cell.number_format = r'[>=100000]₹##\,##\,##0.00;[>=1000]₹##\,##0.00;₹##0.00'
            elif col_name == 'Increase %':
                if isinstance(cell.value, (int, float)):
                    cell.number_format = '0.00%'
            elif col_name in ['Purchase Year WPI', 'Current Year WPI']:
                if isinstance(cell.value, (int, float)):
                    cell.number_format = '0.000000'
            elif isinstance(cell.value, (datetime.date, datetime.datetime)):
                cell.number_format = 'yyyy-mm-dd'

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    # -------------------------------------------------------------
    # SHEET 2: Summary
    # -------------------------------------------------------------
    ws_sum = wb.create_sheet("Summary")
    total_acq = float(analysis.total_acquisition or 0.0)
    total_rep = float(analysis.total_replacement or 0.0)
    total_diff = total_rep - total_acq
    inc_pct_total = (total_diff / total_acq) if total_acq > 0 else 0.0

    summary_rows = [
        ["Metric", "Value"],
        ["Total Assets", int(analysis.rows_total or 0)],
        ["Calculated Assets", int(analysis.rows_calculated or 0)],
        ["Manual Review Count", int(analysis.rows_manual_review or 0)],
        ["Not Applicable Count", int(analysis.rows_not_applicable or 0)],
        ["Total Acquisition Value", total_acq],
        ["Total Replacement Value", total_rep],
        ["Total Difference", total_diff],
        ["Overall Increase %", inc_pct_total],
        ["Calculation Year", LATEST_WPI_YEAR],
        ["Methodology Note", "Replacement values calculated using the approved WPI/special-category methodologies with reference year 2025."]
    ]

    summary_rows.append(["", ""])
    summary_rows.append(["WPI Category", "Count of Assets"])
    for wpi_cat, count in wpi_category_counts.items():
        summary_rows.append([wpi_cat, count])

    for r_idx, r_data in enumerate(summary_rows, 1):
        ws_sum.cell(row=r_idx, column=1, value=r_data[0])
        if len(r_data) > 1:
            c = ws_sum.cell(row=r_idx, column=2, value=r_data[1])
            if r_data[0] in ["Total Acquisition Value", "Total Replacement Value", "Total Difference"]:
                c.number_format = r'[>=100000]₹##\,##\,##0.00;[>=1000]₹##\,##0.00;₹##0.00'
            elif r_data[0] == "Overall Increase %":
                c.number_format = '0.00%'

        if r_idx == 1 or r_data[0] == "WPI Category":
            ws_sum.cell(row=r_idx, column=1).font = Font(bold=True)
            if len(r_data) > 1:
                ws_sum.cell(row=r_idx, column=2).font = Font(bold=True)

    ws_sum.column_dimensions['A'].width = 30
    ws_sum.column_dimensions['B'].width = 35

    # Save to memory stream
    output_stream = io.BytesIO()
    wb.save(output_stream)
    wb.close()
    output_stream.seek(0)
    return output_stream
