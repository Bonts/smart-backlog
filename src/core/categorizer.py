"""AI categorization engine."""

from __future__ import annotations

import json

from ..services.llm import CATEGORIZE_PROMPT, get_llm
from ..storage.database import Database
from .models import EisenhowerQuadrant, Domain, Item


async def categorize_item(item: Item, db: Database) -> Item:
    """Use AI to categorize, tag, and prioritize an item."""
    llm = get_llm()
    categories = [c.name for c in db.list_categories()]
    tags = [t.name for t in db.list_tags()]

    chain = CATEGORIZE_PROMPT | llm
    response = await chain.ainvoke({
        "categories": ", ".join(categories) if categories else "none yet",
        "tags": ", ".join(tags) if tags else "none yet",
        "title": item.title,
        "content": item.content or item.raw_input,
        "item_type": item.item_type.value,
    })

    try:
        result = json.loads(response.content)
    except (json.JSONDecodeError, AttributeError):
        return item

    # Apply AI suggestions
    item.ai_suggested_category = result.get("category")
    item.ai_suggested_tags = result.get("tags", [])
    item.ai_summary = result.get("summary")

    quadrant = result.get("quadrant")
    if quadrant and quadrant in [q.value for q in EisenhowerQuadrant]:
        item.ai_suggested_quadrant = EisenhowerQuadrant(quadrant)
        item.quadrant = item.quadrant or item.ai_suggested_quadrant

    domain = result.get("domain")
    if domain and domain in [d.value for d in Domain]:
        item.domain = item.domain or Domain(domain)

    return item
