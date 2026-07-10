"""PDF export helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from io import BytesIO

from config import EXPORTS_DIR


def export_text_report(analysis: dict[str, Any], filename: str = "expense_audit_report.txt") -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    target = EXPORTS_DIR / filename
    target.write_text(str(analysis), encoding="utf-8")
    return target


def build_pdf_bytes(report_text: str) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=landscape(A4), title="Expense Audit Report")
    styles = getSampleStyleSheet()
    story = [Paragraph("Expense Audit Report", styles["Title"]), Spacer(1, 12)]

    for block in report_text.split("\n\n"):
        html_safe = block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(html_safe.replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 10))

    document.build(story)
    return buffer.getvalue()


def build_audit_pdf_bytes(title: str, summary: list[str], rows: list[dict[str, Any]]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    def cell(value: Any) -> Paragraph:
        text = str(value or "").replace("\n", "<br/>")
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(text, cell_style)

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        title=title,
        leftMargin=18,
        rightMargin=18,
        topMargin=24,
        bottomMargin=24,
    )
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        "AuditTableCell",
        parent=styles["BodyText"],
        fontSize=6.5,
        leading=8,
        wordWrap="CJK",
    )
    header_style = ParagraphStyle(
        "AuditTableHeader",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = [Paragraph(title, styles["Title"]), Spacer(1, 8)]
    for line in summary:
        story.append(Paragraph(line, styles["BodyText"]))
    story.append(Spacer(1, 10))

    columns = [
        ("Claim ID", 54),
        ("Employee", 70),
        ("Vendor", 72),
        ("Amount", 52),
        ("Date", 54),
        ("Decision", 58),
        ("Risk", 34),
        ("Severity", 44),
        ("Confidence", 48),
        ("Issue", 142),
        ("Next Action", 176),
    ]
    table_data = [[Paragraph(name, header_style) for name, _ in columns]]
    for row in rows:
        table_data.append(
            [
                cell(row.get("Claim ID", "")),
                cell(row.get("Employee", "")),
                cell(row.get("Vendor", "")),
                cell(row.get("Amount", "")),
                cell(row.get("Date", "")),
                cell(row.get("Decision", "")),
                cell(row.get("Risk Score", "")),
                cell(row.get("Severity", "")),
                cell(row.get("Confidence", "")),
                cell(row.get("Issue", "")),
                cell(row.get("Next Action", "")),
            ]
        )

    table = Table(table_data, colWidths=[width for _, width in columns], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    document.build(story)
    return buffer.getvalue()
