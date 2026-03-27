"""PDF export for Smart Backlog — beautiful table views."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..core.models import EisenhowerQuadrant, Item, ItemKind, KanbanState

# --- Color Palette ---
HEADER_BG = colors.HexColor("#2D3748")
HEADER_FG = colors.white
ROW_EVEN = colors.HexColor("#F7FAFC")
ROW_ODD = colors.white
ACCENT_RED = colors.HexColor("#E53E3E")
ACCENT_YELLOW = colors.HexColor("#D69E2E")
ACCENT_ORANGE = colors.HexColor("#DD6B20")
ACCENT_GRAY = colors.HexColor("#A0AEC0")
KIND_TASK = colors.HexColor("#3182CE")
KIND_NOTE = colors.HexColor("#38A169")
KIND_IDEA = colors.HexColor("#D69E2E")


def _quadrant_label(q: Optional[EisenhowerQuadrant]) -> str:
    if not q:
        return "—"
    return {
        EisenhowerQuadrant.DO_FIRST: "🔴 Do First",
        EisenhowerQuadrant.SCHEDULE: "🟡 Schedule",
        EisenhowerQuadrant.DELEGATE: "🟠 Delegate",
        EisenhowerQuadrant.ELIMINATE: "⚪ Eliminate",
    }.get(q, q.value)


def _state_label(s: KanbanState) -> str:
    return {
        KanbanState.BACKLOG: "Backlog",
        KanbanState.TODO: "To Do",
        KanbanState.IN_PROGRESS: "In Progress",
        KanbanState.DONE: "Done",
        KanbanState.ARCHIVED: "Archived",
    }.get(s, s.value)


def _kind_label(k: ItemKind) -> str:
    return {"task": "Task", "note": "Note", "idea": "Idea"}.get(k.value, k.value)


def _domain_label(d) -> str:
    if not d:
        return "—"
    return {"work": "Work", "personal": "Personal", "study": "Study"}.get(d.value, d.value)


def generate_backlog_pdf(items: list[Item], title: str = "Smart Backlog") -> bytes:
    """Generate a landscape PDF with all items in a styled table. Returns PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PDFTitle", parent=styles["Title"], fontSize=18, spaceAfter=4 * mm,
    )
    subtitle_style = ParagraphStyle(
        "PDFSubtitle", parent=styles["Normal"], fontSize=9, textColor=colors.gray,
    )
    cell_style = ParagraphStyle(
        "Cell", parent=styles["Normal"], fontSize=8, leading=10,
    )
    header_style = ParagraphStyle(
        "HeaderCell", parent=styles["Normal"], fontSize=8, leading=10,
        textColor=HEADER_FG, fontName="Helvetica-Bold",
    )

    elements = []
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(
        f"Generated {datetime.now().strftime('%d.%m.%Y %H:%M')}  •  {len(items)} items",
        subtitle_style,
    ))
    elements.append(Spacer(1, 4 * mm))

    # Table header
    headers = ["#", "Kind", "Title", "Category", "Domain", "Priority", "Status", "Due", "Summary"]
    header_row = [Paragraph(h, header_style) for h in headers]

    # Table data
    data = [header_row]
    for i, item in enumerate(items, 1):
        due = item.deadline.strftime("%d.%m.%Y") if item.deadline else "—"
        summary = (item.ai_summary or "")[:80]
        if len(item.ai_summary or "") > 80:
            summary += "…"
        row = [
            Paragraph(str(i), cell_style),
            Paragraph(_kind_label(item.kind), cell_style),
            Paragraph(item.title[:50], cell_style),
            Paragraph((item.ai_suggested_category or "—")[:25], cell_style),
            Paragraph(_domain_label(item.domain), cell_style),
            Paragraph(_quadrant_label(item.quadrant), cell_style),
            Paragraph(_state_label(item.kanban_state), cell_style),
            Paragraph(due, cell_style),
            Paragraph(summary, cell_style),
        ]
        data.append(row)

    # Column widths (landscape A4 = ~277mm usable)
    col_widths = [8 * mm, 14 * mm, 55 * mm, 30 * mm, 22 * mm, 25 * mm, 22 * mm, 22 * mm, 70 * mm]

    table = Table(data, colWidths=col_widths, repeatRows=1)

    # Style
    style_cmds = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E0")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, HEADER_BG),
        # Alignment
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]

    # Alternating row colors
    for row_idx in range(1, len(data)):
        bg = ROW_EVEN if row_idx % 2 == 0 else ROW_ODD
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))

    table.setStyle(TableStyle(style_cmds))
    elements.append(table)

    doc.build(elements)
    return buf.getvalue()


def generate_matrix_pdf(items: list[Item]) -> bytes:
    """Generate a 2x2 Eisenhower matrix PDF. Returns PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PDFTitle", parent=styles["Title"], fontSize=18, spaceAfter=2 * mm,
    )
    subtitle_style = ParagraphStyle(
        "PDFSubtitle", parent=styles["Normal"], fontSize=9, textColor=colors.gray,
    )
    cell_style = ParagraphStyle(
        "QCell", parent=styles["Normal"], fontSize=8, leading=10,
    )
    q_title_style = ParagraphStyle(
        "QTitle", parent=styles["Normal"], fontSize=10, leading=12,
        fontName="Helvetica-Bold",
    )

    elements = []
    elements.append(Paragraph("Eisenhower Matrix", title_style))
    elements.append(Paragraph(
        f"Generated {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        subtitle_style,
    ))
    elements.append(Spacer(1, 4 * mm))

    # Group items by quadrant
    quadrants = {
        EisenhowerQuadrant.DO_FIRST: [],
        EisenhowerQuadrant.SCHEDULE: [],
        EisenhowerQuadrant.DELEGATE: [],
        EisenhowerQuadrant.ELIMINATE: [],
    }
    for item in items:
        if item.quadrant and item.quadrant in quadrants:
            quadrants[item.quadrant].append(item)

    def _q_cell(label: str, color: colors.HexColor, q_items: list[Item]) -> list:
        parts = [Paragraph(f"<b>{label}</b> ({len(q_items)})", q_title_style)]
        for item in q_items[:10]:
            due = f"  📅{item.deadline.strftime('%d.%m')}" if item.deadline else ""
            parts.append(Paragraph(f"• {item.title[:40]}{due}", cell_style))
        if len(q_items) > 10:
            parts.append(Paragraph(f"... +{len(q_items) - 10} more", cell_style))
        return parts

    # Build 2x2 grid
    q1 = _q_cell("🔴 DO FIRST (Urgent + Important)", ACCENT_RED,
                  quadrants[EisenhowerQuadrant.DO_FIRST])
    q2 = _q_cell("🟡 SCHEDULE (Not Urgent + Important)", ACCENT_YELLOW,
                  quadrants[EisenhowerQuadrant.SCHEDULE])
    q3 = _q_cell("🟠 DELEGATE (Urgent + Not Important)", ACCENT_ORANGE,
                  quadrants[EisenhowerQuadrant.DELEGATE])
    q4 = _q_cell("⚪ ELIMINATE (Not Urgent + Not Important)", ACCENT_GRAY,
                  quadrants[EisenhowerQuadrant.ELIMINATE])

    half_w = 130 * mm
    matrix_data = [
        [q1, q2],
        [q3, q4],
    ]
    matrix = Table(matrix_data, colWidths=[half_w, half_w], rowHeights=[None, None])
    matrix.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#FFF5F5")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFFFF0")),
        ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#FFFAF0")),
        ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#F7FAFC")),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(matrix)

    doc.build(elements)
    return buf.getvalue()
