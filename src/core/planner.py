"""Daily plan generator."""

from __future__ import annotations

import json
from datetime import date

from ..core.models import DailyPlan, KanbanState
from ..services.llm import DAILY_PLAN_PROMPT, get_llm
from ..storage.database import Database


async def generate_daily_plan(db: Database) -> DailyPlan:
    """Generate a focused daily plan from the backlog."""
    today = date.today().isoformat()

    # Get active items (not done/archived)
    items = db.list_items(limit=100)
    active_items = [
        i for i in items
        if i.kanban_state not in (KanbanState.DONE, KanbanState.ARCHIVED)
    ]

    if not active_items:
        return DailyPlan(date=today, summary="No active items in backlog.")

    # Format items for LLM
    items_text = "\n".join(
        f"- ID: {i.id} | Title: {i.title} | Priority: {i.quadrant.value if i.quadrant else 'none'} "
        f"| Domain: {i.domain.value if i.domain else 'none'} | Deadline: {i.deadline or 'none'}"
        for i in active_items
    )

    llm = get_llm()
    chain = DAILY_PLAN_PROMPT | llm
    response = await chain.ainvoke({"date": today, "items": items_text})

    try:
        result = json.loads(response.content)
        plan = DailyPlan(
            date=today,
            items=result.get("selected_item_ids", []),
            summary=result.get("summary", ""),
        )
    except (json.JSONDecodeError, AttributeError):
        plan = DailyPlan(
            date=today,
            items=[i.id for i in active_items[:5]],
            summary="Auto-selected top 5 items.",
        )

    db.save_daily_plan(plan)
    return plan
