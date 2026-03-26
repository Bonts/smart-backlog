"""Input processing pipeline — routes incoming data through appropriate services."""

from __future__ import annotations

import re
from ..core.models import Item, ItemType
from ..services.web_scraper import extract_url_title
from ..storage.database import Database
from .categorizer import categorize_item


URL_PATTERN = re.compile(r"https?://\S+")


async def process_input(
    text: str = "",
    image_path: str | None = None,
    audio_path: str | None = None,
    db: Database | None = None,
) -> list[Item]:
    """Process raw input and return categorized Item(s)."""
    db = db or Database()
    items: list[Item] = []

    # URL input
    if text and URL_PATTERN.match(text.strip()):
        item = await _process_url(text.strip())
        items.append(item)

    # Image input
    elif image_path:
        item = await _process_image(image_path)
        items.append(item)

    # Audio input
    elif audio_path:
        items.extend(await _process_audio(audio_path))

    # Plain text
    elif text:
        item = Item(title=text[:100], content=text, raw_input=text, item_type=ItemType.NOTE)
        items.append(item)

    # Categorize all items
    for i, item in enumerate(items):
        items[i] = await categorize_item(item, db)

    return items


async def _process_url(url: str) -> Item:
    """Process a URL — extract title."""
    try:
        title = await extract_url_title(url)
    except Exception:
        title = url
    return Item(title=title, url=url, raw_input=url, item_type=ItemType.URL)


async def _process_image(image_path: str) -> Item:
    """Process a screenshot — OCR and interpret."""
    from ..services.ocr import extract_text_from_image
    text = await extract_text_from_image(image_path)
    return Item(
        title=text[:100] if text else "Screenshot",
        content=text,
        raw_input=f"[screenshot: {image_path}]",
        item_type=ItemType.SCREENSHOT,
    )


async def _process_audio(audio_path: str) -> list[Item]:
    """Process audio — transcribe and extract tasks."""
    import json
    from ..services.transcriber import transcribe_audio
    from ..services.llm import VOICE_TO_TASKS_PROMPT, get_llm

    transcription = await transcribe_audio(audio_path)

    # Extract tasks from transcription
    llm = get_llm()
    chain = VOICE_TO_TASKS_PROMPT | llm
    response = await chain.ainvoke({"transcription": transcription})

    items = []
    try:
        result = json.loads(response.content)
        for task in result.get("tasks", []):
            item = Item(
                title=task["title"],
                content=task.get("context", ""),
                raw_input=transcription,
                item_type=ItemType.VOICE,
            )
            items.append(item)
    except (json.JSONDecodeError, AttributeError):
        # Fallback: create single item from transcription
        items.append(Item(
            title=transcription[:100],
            content=transcription,
            raw_input=transcription,
            item_type=ItemType.VOICE,
        ))

    return items
