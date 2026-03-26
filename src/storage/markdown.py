"""Markdown export for mobile-friendly viewing."""

from __future__ import annotations

from ..core.models import DailyPlan, EisenhowerQuadrant, Item


def item_to_markdown(item: Item) -> str:
    """Convert an Item to a mobile-friendly Markdown string."""
    lines = [f"## {item.title}", ""]

    if item.url:
        lines.append(f"- **Link**: {item.url}")
    if item.domain:
        lines.append(f"- **Domain**: {item.domain.value}")
    if item.quadrant:
        labels = {
            EisenhowerQuadrant.DO_FIRST: "DO FIRST (urgent + important)",
            EisenhowerQuadrant.SCHEDULE: "SCHEDULE (important)",
            EisenhowerQuadrant.DELEGATE: "DELEGATE (urgent)",
            EisenhowerQuadrant.ELIMINATE: "ELIMINATE (neither)",
        }
        lines.append(f"- **Priority**: {labels.get(item.quadrant, item.quadrant.value)}")
    if item.tags:
        lines.append(f"- **Tags**: {', '.join(item.tags)}")
    if item.kanban_state:
        lines.append(f"- **Status**: {item.kanban_state.value}")

    lines.append("")
    if item.ai_summary:
        lines.extend(["### Summary", "", item.ai_summary, ""])
    if item.content:
        lines.extend(["### Content", "", item.content, ""])

    return "\n".join(lines)


def daily_plan_to_markdown(plan: DailyPlan, items: list[Item]) -> str:
    """Convert a DailyPlan to mobile-friendly Markdown."""
    lines = [f"# Daily Plan — {plan.date}", ""]
    if plan.summary:
        lines.extend([plan.summary, ""])

    for i, item in enumerate(items, 1):
        status = "[ ]" if item.kanban_state.value != "done" else "[x]"
        domain_badge = f" `{item.domain.value}`" if item.domain else ""
        lines.append(f"- {status} **{i}. {item.title}**{domain_badge}")
        if item.ai_summary:
            lines.append(f"  - {item.ai_summary}")

    lines.append("")
    return "\n".join(lines)
