"""Eisenhower matrix prioritization logic."""

from __future__ import annotations

from ..core.models import EisenhowerQuadrant, Item


def get_eisenhower_matrix(items: list[Item]) -> dict[str, list[Item]]:
    """Group items by Eisenhower quadrant."""
    matrix = {
        EisenhowerQuadrant.DO_FIRST.value: [],
        EisenhowerQuadrant.SCHEDULE.value: [],
        EisenhowerQuadrant.DELEGATE.value: [],
        EisenhowerQuadrant.ELIMINATE.value: [],
        "unclassified": [],
    }
    for item in items:
        key = item.quadrant.value if item.quadrant else "unclassified"
        matrix[key].append(item)
    return matrix


def matrix_to_markdown(matrix: dict[str, list[Item]]) -> str:
    """Render Eisenhower matrix as Markdown."""
    labels = {
        "do_first": "🔴 DO FIRST (Urgent + Important)",
        "schedule": "🟡 SCHEDULE (Important, Not Urgent)",
        "delegate": "🟠 DELEGATE (Urgent, Not Important)",
        "eliminate": "⚪ ELIMINATE (Neither)",
        "unclassified": "❓ UNCLASSIFIED",
    }
    lines = ["# Eisenhower Matrix", ""]
    for quadrant, items in matrix.items():
        if not items:
            continue
        lines.append(f"## {labels.get(quadrant, quadrant)}")
        for item in items:
            domain = f" `{item.domain.value}`" if item.domain else ""
            lines.append(f"- {item.title}{domain}")
        lines.append("")
    return "\n".join(lines)
