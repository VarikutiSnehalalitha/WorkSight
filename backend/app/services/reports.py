"""Enterprise Excel (.xlsx) and PDF (.pdf) Report Generators for WorkSight."""

import io
from datetime import date
from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_attendance_excel(
    start_date: date,
    end_date: date,
    department_summaries: List[Dict[str, Any]],
    records: List[Dict[str, Any]],
) -> bytes:
    wb = Workbook()

    # Sheet 1: Executive Department Summary
    ws_sum = wb.active
    ws_sum.title = "Department Summary"

    header_fill = PatternFill(start_color="284B3C", end_color="284B3C", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    title_font = Font(color="1B211E", bold=True, size=14)
    note_font = Font(color="636B66", italic=True, size=9)

    ws_sum["A1"] = "WorkSight — Verified Attendance & Workplace Summary"
    ws_sum["A1"].font = title_font
    ws_sum["A2"] = f"Reporting Window: {start_date.isoformat()} to {end_date.isoformat()}"
    ws_sum["A3"] = (
        "Ethical Governance Notice: Individual attendance reflects verified access-card/QR/portal "
        "check-ins only. Physical presence is not a measurement of employee productivity."
    )
    ws_sum["A3"].font = note_font

    sum_headers = [
        "Department",
        "Code",
        "Employees",
        "Present Records",
        "Late Arrivals",
        "Early Departures",
        "On Leave",
        "Avg Working Hours",
        "Attendance Rate (%)",
    ]
    ws_sum.append([])
    ws_sum.append(sum_headers)
    for col_idx in range(1, len(sum_headers) + 1):
        cell = ws_sum.cell(row=5, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for dept in department_summaries:
        ws_sum.append(
            [
                dept["department_name"],
                dept["department_code"],
                dept["employee_count"],
                dept["present_records"],
                dept["late_records"],
                dept["early_departures"],
                dept["leave_records"],
                dept["avg_working_hours"],
                dept["attendance_rate"],
            ]
        )

    for col in ws_sum.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws_sum.column_dimensions[col[0].column_letter].width = min(max_len + 4, 38)

    # Sheet 2: Detailed Verified Attendance Log
    ws_det = wb.create_sheet(title="Verified Attendance Log")
    det_headers = [
        "Date",
        "Employee Code",
        "Employee Name",
        "Department",
        "Check-In (UTC)",
        "Check-Out (UTC)",
        "Status",
        "Working Hours",
        "Late (min)",
        "Early Out (min)",
        "Verification Method",
    ]
    ws_det.append(det_headers)
    for col_idx in range(1, len(det_headers) + 1):
        cell = ws_det.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for rec in records:
        ws_det.append(
            [
                rec["attendance_date"],
                rec["employee_code"],
                rec["employee_name"],
                rec["department_name"],
                rec["check_in_time"] or "-",
                rec["check_out_time"] or "-",
                rec["status"],
                rec["working_hours"],
                rec["late_minutes"],
                rec["early_departure_minutes"],
                rec["verification_method"],
            ]
        )

    for col in ws_det.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws_det.column_dimensions[col[0].column_letter].width = min(max_len + 4, 34)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def generate_attendance_pdf(
    start_date: date,
    end_date: date,
    department_summaries: List[Dict[str, Any]],
    records: List[Dict[str, Any]],
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "WorkSightTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#1B211E"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "WorkSightSub",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#4F7665"),
        spaceAfter=8,
    )
    note_style = ParagraphStyle(
        "WorkSightNote",
        parent=styles["Italic"],
        fontSize=8.5,
        textColor=colors.HexColor("#636B66"),
        spaceAfter=12,
    )

    elements = [
        Paragraph("WorkSight — Verified Attendance & Department Report", title_style),
        Paragraph(
            f"Reporting Window: {start_date.isoformat()} to {end_date.isoformat()}  |  "
            f"Total Verified Records: {len(records)}",
            subtitle_style,
        ),
        Paragraph(
            "Privacy & Ethics Disclosure: Attendance attribution uses verified access cards, QR check-in, "
            "or HR-approved records. Physical presence telemetry does not establish individual productivity, "
            "and human review is required before any employment decision.",
            note_style,
        ),
    ]

    # Department Summary Table
    sum_data = [
        [
            "Department",
            "Code",
            "Headcount",
            "Present",
            "Late",
            "Early Out",
            "Leave",
            "Avg Hrs",
            "Rate %",
        ]
    ]
    for d in department_summaries:
        sum_data.append(
            [
                d["department_name"],
                d["department_code"],
                str(d["employee_count"]),
                str(d["present_records"]),
                str(d["late_records"]),
                str(d["early_departures"]),
                str(d["leave_records"]),
                f"{d['avg_working_hours']:.1f}",
                f"{d['attendance_rate']:.1f}%",
            ]
        )

    sum_table = Table(sum_data, repeatRows=1)
    sum_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#284B3C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#F7F5F0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F5F0")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8D2C5")),
                ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(sum_table)
    elements.append(Spacer(1, 10 * mm))

    # Detailed Log Table (up to 80 most recent rows for concise executive PDF)
    elements.append(Paragraph("Detailed Verified Attendance Log (Recent Entries)", styles["Heading3"]))
    det_data = [
        [
            "Date",
            "Code",
            "Employee",
            "Department",
            "Check-In",
            "Check-Out",
            "Status",
            "Hours",
            "Method",
        ]
    ]
    for r in records[:80]:
        det_data.append(
            [
                r["attendance_date"],
                r["employee_code"],
                r["employee_name"],
                r["department_name"],
                (r["check_in_time"] or "-")[:16].replace("T", " "),
                (r["check_out_time"] or "-")[:16].replace("T", " "),
                r["status"],
                f"{r['working_hours']:.2f}",
                r["verification_method"],
            ]
        )

    det_table = Table(det_data, repeatRows=1)
    det_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3E5F50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAF8F4")]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2DDD2")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(det_table)

    doc.build(elements)
    return buf.getvalue()
