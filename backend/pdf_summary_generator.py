import os
import io
import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    HRFlowable
)
from reportlab.pdfgen import canvas

import models
import calculator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_GROUPS_ORDER = [
    "Building",
    "Land",
    "Plant & Machinery",
    "Computer",
    "Furniture & Fixture",
    "Office Equipment",
    "Vehicles",
    "Software",
    "Needs review"
]

def format_inr(val: float | int | None) -> str:
    """Formats a float/int value into Indian numbering system (Lakhs & Crores) with 2 decimals."""
    if val is None:
        return "0.00"
    try:
        val = float(val)
    except (ValueError, TypeError):
        return "0.00"
    is_neg = val < 0
    val = round(abs(val), 2)
    parts = f"{val:.2f}".split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last3 = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted = ",".join(groups) + "," + last3

    res = f"{formatted}.{decimal_part}"
    return f"-{res}" if is_neg else res

def format_count(val: int | None) -> str:
    """Formats an integer into Indian comma-separated format."""
    if val is None:
        return "0"
    val = int(val)
    is_neg = val < 0
    val = abs(val)
    s = str(val)
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        remaining = s[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted = ",".join(groups) + "," + last3
    return f"-{formatted}" if is_neg else formatted

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw 'Page X of Y' in footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Subtle footer divider
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 32, 595.27 - 36, 32)

        # Footer Left: Confidentiality notice (NO user name, NO prepared by)
        self.drawString(36, 22, "Confidential — Assetra Valuation Summary Report")
        
        # Footer Right: Page X of Y
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(595.27 - 36, 22, page_str)
        self.restoreState()

def fetch_grouped_data(db: Session, analysis_id: int) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]], List[str], Dict[str, Any]]:
    """
    Executes SQL grouping over analysis_rows without recalculation or Gemini calls.
    Returns:
    - grand_total_rows: [{Particulars, count, cost, replacement, increase_pct}]
    - location_rows: {location_name: [{Particulars, count, cost, replacement, increase_pct}]}
    - distinct_locations: [loc1, loc2, ...]
    - held_at_cost: {count, cost}
    """
    ref_year = getattr(calculator, "REFERENCE_YEAR", 2025)

    # 1. Distinct locations query
    loc_query = text("""
        SELECT DISTINCT TRIM(location) AS loc
        FROM analysis_rows
        WHERE analysis_id = :aid AND location IS NOT NULL AND TRIM(location) != ''
        ORDER BY loc
    """)
    loc_res = db.execute(loc_query, {"aid": analysis_id}).fetchall()
    distinct_locations = [r[0] for r in loc_res if r[0]]

    # 2. Overall aggregation grouped by asset category
    group_sql = text("""
        SELECT
            CASE
                WHEN status IN ('Manual Review Required', 'Needs Mapping', 'Data Missing', 'WPI Data Missing')
                     OR status LIKE '%Manual%' OR status LIKE '%Failed%' THEN 'Needs review'
                WHEN wpi_group = 'Building' THEN 'Building'
                WHEN wpi_group = 'Land' THEN 'Land'
                WHEN wpi_group = 'Plant & Machinery' THEN 'Plant & Machinery'
                WHEN wpi_group = 'Computer' THEN 'Computer'
                WHEN wpi_group = 'Furniture & Fixture' THEN 'Furniture & Fixture'
                WHEN wpi_group = 'Office Equipment' THEN 'Office Equipment'
                WHEN wpi_group IN ('Vehicles', 'Vehicle') THEN 'Vehicles'
                WHEN wpi_group = 'Software' THEN 'Software'
                ELSE 'Needs review'
            END AS asset_group,
            COUNT(id) AS asset_count,
            COALESCE(SUM(acquisition_value), 0.0) AS total_cost,
            COALESCE(SUM(replacement_value), 0.0) AS total_rep
        FROM analysis_rows
        WHERE analysis_id = :aid
        GROUP BY asset_group
    """)
    overall_res = db.execute(group_sql, {"aid": analysis_id}).fetchall()
    overall_dict = {
        r[0]: {
            "count": int(r[1]),
            "cost": float(r[2]),
            "replacement": float(r[3])
        } for r in overall_res
    }

    grand_total_rows = []
    for g in ASSET_GROUPS_ORDER:
        if g in overall_dict and overall_dict[g]["count"] > 0:
            d = overall_dict[g]
            c = d["cost"]
            rep = d["replacement"]
            inc_pct = ((rep - c) / c * 100.0) if c > 0 else 0.0
            grand_total_rows.append({
                "group": g,
                "count": d["count"],
                "cost": c,
                "replacement": rep,
                "increase_pct": inc_pct
            })

    # Reconcile minor sub-cent/paisa rounding residuals against the analysis header metrics
    # so that the PDF grand totals equal the dashboard metrics exactly to the paisa.
    analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()
    if analysis and grand_total_rows:
        dash_cost = float(analysis.total_acquisition or 0.0)
        dash_rep = float(analysis.total_replacement or 0.0)
        sum_cost = sum(r["cost"] for r in grand_total_rows)
        cost_diff = round(dash_cost - sum_cost, 2)
        sum_rep = sum(r["replacement"] for r in grand_total_rows)
        rep_diff = round(dash_rep - sum_rep, 2)

        if abs(cost_diff) > 0 and abs(cost_diff) < 5.0:
            largest_cost_row = max(grand_total_rows, key=lambda x: x["cost"])
            largest_cost_row["cost"] = round(largest_cost_row["cost"] + cost_diff, 2)
            c = largest_cost_row["cost"]
            rep = largest_cost_row["replacement"]
            largest_cost_row["increase_pct"] = ((rep - c) / c * 100.0) if c > 0 else 0.0

        if abs(rep_diff) > 0 and abs(rep_diff) < 5.0:
            largest_rep_row = max(grand_total_rows, key=lambda x: x["replacement"])
            largest_rep_row["replacement"] = round(largest_rep_row["replacement"] + rep_diff, 2)
            c = largest_rep_row["cost"]
            rep = largest_rep_row["replacement"]
            largest_rep_row["increase_pct"] = ((rep - c) / c * 100.0) if c > 0 else 0.0

    # 3. Location breakdown query if multiple locations exist
    location_rows = {}
    if len(distinct_locations) > 1:
        loc_group_sql = text("""
            SELECT
                COALESCE(NULLIF(TRIM(location), ''), 'Unspecified') AS loc_name,
                CASE
                    WHEN status IN ('Manual Review Required', 'Needs Mapping', 'Data Missing', 'WPI Data Missing')
                         OR status LIKE '%Manual%' OR status LIKE '%Failed%' THEN 'Needs review'
                    WHEN wpi_group = 'Building' THEN 'Building'
                    WHEN wpi_group = 'Land' THEN 'Land'
                    WHEN wpi_group = 'Plant & Machinery' THEN 'Plant & Machinery'
                    WHEN wpi_group = 'Computer' THEN 'Computer'
                    WHEN wpi_group = 'Furniture & Fixture' THEN 'Furniture & Fixture'
                    WHEN wpi_group = 'Office Equipment' THEN 'Office Equipment'
                    WHEN wpi_group IN ('Vehicles', 'Vehicle') THEN 'Vehicles'
                    WHEN wpi_group = 'Software' THEN 'Software'
                    ELSE 'Needs review'
                END AS asset_group,
                COUNT(id) AS asset_count,
                COALESCE(SUM(acquisition_value), 0.0) AS total_cost,
                COALESCE(SUM(replacement_value), 0.0) AS total_rep
            FROM analysis_rows
            WHERE analysis_id = :aid
            GROUP BY loc_name, asset_group
        """)
        loc_res_all = db.execute(loc_group_sql, {"aid": analysis_id}).fetchall()
        loc_data_map: Dict[str, Dict[str, Any]] = {}
        for r in loc_res_all:
            l_name = r[0]
            g_name = r[1]
            if l_name not in loc_data_map:
                loc_data_map[l_name] = {}
            loc_data_map[l_name][g_name] = {
                "count": int(r[2]),
                "cost": float(r[3]),
                "replacement": float(r[4])
            }

        # Build ordered list for each location, omitting empty groups
        for l_name, g_map in loc_data_map.items():
            loc_list = []
            for g in ASSET_GROUPS_ORDER:
                if g in g_map and g_map[g]["count"] > 0:
                    d = g_map[g]
                    c = d["cost"]
                    rep = d["replacement"]
                    inc = ((rep - c) / c * 100.0) if c > 0 else 0.0
                    loc_list.append({
                        "group": g,
                        "count": d["count"],
                        "cost": c,
                        "replacement": rep,
                        "increase_pct": inc
                    })
            if loc_list:
                location_rows[l_name] = loc_list

    # 4. Held at cost calculation (Software, post-ref additions, manual review rows)
    held_sql = text("""
        SELECT
            COUNT(id) AS held_count,
            COALESCE(SUM(acquisition_value), 0.0) AS held_cost
        FROM analysis_rows
        WHERE analysis_id = :aid
          AND (
              wpi_group = 'Software'
              OR (purchase_year IS NOT NULL AND purchase_year > :ref_year)
              OR status IN ('Manual Review Required', 'Needs Mapping', 'Data Missing', 'WPI Data Missing', 'Not Applicable')
              OR status LIKE '%Manual%'
              OR status LIKE '%Failed%'
              OR calculation_method LIKE '%At Cost%'
              OR calculation_method = 'Not Applicable'
          )
    """)
    held_res = db.execute(held_sql, {"aid": analysis_id, "ref_year": ref_year}).fetchone()
    held_at_cost = {
        "count": int(held_res[0]) if held_res and held_res[0] else 0,
        "cost": float(held_res[1]) if held_res and held_res[1] else 0.0
    }

    return grand_total_rows, location_rows, distinct_locations, held_at_cost

def build_pdf_table(data_rows: List[Dict[str, Any]], table_title: str = "") -> Table:
    """Builds a formatted ReportLab Table for an asset grouping with bold Total row."""
    # Table header
    headers = [
        "Particulars",
        "Number of assets",
        "Capitalized cost (INR)",
        "New replacement value (INR)",
        "Increase %"
    ]
    
    rows = [headers]
    tot_count = 0
    tot_cost = 0.0
    tot_rep = 0.0

    for r in data_rows:
        tot_count += r["count"]
        tot_cost += r["cost"]
        tot_rep += r["replacement"]
        inc_str = f"{r['increase_pct']:.1f}%" if r["cost"] > 0 else "-"
        rows.append([
            r["group"],
            format_count(r["count"]),
            format_inr(r["cost"]),
            format_inr(r["replacement"]),
            inc_str
        ])

    tot_inc_pct = ((tot_rep - tot_cost) / tot_cost * 100.0) if tot_cost > 0 else 0.0
    tot_inc_str = f"{tot_inc_pct:.1f}%" if tot_cost > 0 else "-"
    rows.append([
        "Total",
        format_count(tot_count),
        format_inr(tot_cost),
        format_inr(tot_rep),
        tot_inc_str
    ])

    # Printable width is 523.27pt on A4 (595.27 - 72)
    col_widths = [163, 75, 110, 115, 60]
    
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A192F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -2), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        # Total row (last row) styling
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#0A192F")),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, colors.HexColor("#0A192F")),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, colors.HexColor("#0A192F")),
        # Grid lines
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E2E8F0")),
    ]

    # Alternating row background for data rows
    for i in range(1, len(rows) - 1):
        bg = colors.HexColor("#FFFFFF") if i % 2 != 0 else colors.HexColor("#F8FAFC")
        t_style.append(("BACKGROUND", (0, i), (-1, i), bg))

    table = Table(rows, colWidths=col_widths, style=TableStyle(t_style))
    return table

def generate_pdf_summary_stream(analysis: models.Analysis, db: Session) -> io.BytesIO:
    """
    Generates a professional 1-2 page Valuation Summary PDF using ReportLab.
    Built directly from saved analysis_rows with SQL grouping.
    Zero files stored on disk.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=42
    )

    story = []
    styles = getSampleStyleSheet()
    
    # -------------------------------------------------------------
    # HEADER: Logos & Title
    # -------------------------------------------------------------
    assetra_logo_path = os.path.join(BASE_DIR, "..", "frontend", "public", "Assetra.png")
    share_india_logo_path = os.path.join(BASE_DIR, "..", "frontend", "public", "share_india_logo.png")

    logo_assetra = None
    if os.path.exists(assetra_logo_path):
        logo_assetra = Image(assetra_logo_path, width=32, height=32)
    
    logo_share_india = None
    if os.path.exists(share_india_logo_path):
        logo_share_india = Image(share_india_logo_path, width=32, height=32)

    title_style = ParagraphStyle(
        "HeaderTitle",
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        alignment=1, # Center
        textColor=colors.HexColor("#0A192F")
    )
    subtitle_style = ParagraphStyle(
        "HeaderSubtitle",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=colors.HexColor("#64748B")
    )

    header_cells = [
        [
            logo_assetra if logo_assetra else "",
            [
                Paragraph("VALUATION SUMMARY", title_style),
                Paragraph("Fixed Asset Replacement Value Analysis", subtitle_style)
            ],
            logo_share_india if logo_share_india else ""
        ]
    ]

    header_table = Table(
        header_cells,
        colWidths=[40, 523 - 80, 40],
        style=TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0A192F"), spaceBefore=2, spaceAfter=8))

    # -------------------------------------------------------------
    # METADATA BLOCK
    # -------------------------------------------------------------
    calc_date_str = analysis.created_at.strftime("%d-%b-%Y") if analysis.created_at else datetime.date.today().strftime("%d-%b-%Y")
    ref_year = getattr(calculator, "REFERENCE_YEAR", 2025)
    version_short = analysis.master_version[:8] if analysis.master_version else "v6"

    meta_label = ParagraphStyle("MetaLabel", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=colors.HexColor("#475569"))
    meta_val = ParagraphStyle("MetaVal", fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#0F172A"))

    meta_data = [
        [
            Paragraph("<b>Company Name:</b>", meta_label),
            Paragraph(analysis.company_name or "N/A", meta_val),
            Paragraph("<b>Valuation Date:</b>", meta_label),
            Paragraph(calc_date_str, meta_val)
        ],
        [
            Paragraph("<b>File Name:</b>", meta_label),
            Paragraph(analysis.original_filename or "N/A", meta_val),
            Paragraph("<b>Dataset / Ref Year:</b>", meta_label),
            Paragraph(f"WPI {version_short} / FY {ref_year}", meta_val)
        ]
    ]

    meta_table = Table(
        meta_data,
        colWidths=[80, 180, 100, 163],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # SUMMARY TABLES (SQL Grouping)
    # -------------------------------------------------------------
    grand_rows, loc_rows, distinct_locs, held_at_cost = fetch_grouped_data(db, analysis.id)

    section_style = ParagraphStyle(
        "SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0A192F")
    )

    if len(distinct_locs) > 1 and loc_rows:
        # Multiple locations: Table per location
        for loc_name in sorted(loc_rows.keys()):
            story.append(Paragraph(f"Location: {loc_name}", section_style))
            story.append(Spacer(1, 4))
            story.append(build_pdf_table(loc_rows[loc_name]))
            story.append(Spacer(1, 10))
        
        # Grand Total Table
        story.append(Paragraph("Grand Total Summary (All Locations)", section_style))
        story.append(Spacer(1, 4))
        story.append(build_pdf_table(grand_rows))
    else:
        # Single table
        story.append(Paragraph("Asset Class Valuation Summary", section_style))
        story.append(Spacer(1, 4))
        story.append(build_pdf_table(grand_rows))

    story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # NOTES & DISCLAIMER SECTION
    # -------------------------------------------------------------
    method = getattr(calculator, "BUILDING_AND_LAND_METHOD", "compound").lower()
    method_display = "5% Annual Compound Escalation" if method == "compound" else "5% Annual Simple Escalation"
    b_rate = int(round(getattr(calculator, "BUILDING_ESCALATION_RATE", 0.05) * 100))
    l_rate = int(round(getattr(calculator, "LAND_ESCALATION_RATE", 0.05) * 100))

    notes_style = ParagraphStyle(
        "NotesStyle",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#334155")
    )
    disclaimer_style = ParagraphStyle(
        "DisclaimerStyle",
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#64748B")
    )

    # 1. Held at Cost Line
    held_text = (
        f"<b>Held at cost:</b> {format_count(held_at_cost['count'])} assets "
        f"(INR {format_inr(held_at_cost['cost'])}) — includes Software, purchases after reference year "
        f"({ref_year}), and Manual Review items."
    )
    story.append(Paragraph(held_text, notes_style))
    story.append(Spacer(1, 4))

    # 2. Basis Note read from RULES
    basis_text = (
        f"<b>Basis of Valuation:</b> Plant & Machinery and equipment indexed across official Wholesale Price Index "
        f"(WPI) time series (1961–{ref_year}). Building and Land calculated using {method_display} "
        f"({b_rate}% Building / {l_rate}% Land). Software products and post-{ref_year} additions held at historical capitalized cost."
    )
    story.append(Paragraph(basis_text, notes_style))
    story.append(Spacer(1, 4))

    # 3. Mandatory Disclaimer (no signature, no user name)
    disclaimer_text = "<b>Disclaimer:</b> Estimates based on price-index movements. Not a valuer's certificate or vendor quotation."
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    # Build document with two-pass NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer
