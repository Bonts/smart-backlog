"""Input processing pipeline — routes incoming data through appropriate services."""

from __future__ import annotations

import logging
import re
from ..core.models import Item, ItemType
from ..services.web_scraper import extract_url_title
from ..storage.database import Database
from .categorizer import categorize_item

logger = logging.getLogger(__name__)

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
    import json as _json
    from ..services.ocr import extract_text_from_image
    text = await extract_text_from_image(image_path)

    # Try to parse structured JSON from vision model
    try:
        # Strip markdown code fences if present
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = _json.loads(clean)
        content_type = data.get("type", "other")

        if content_type == "book":
            title_parts = [f"[Book] {data.get('title', 'Unknown')}"]
            if data.get("author"):
                title_parts[0] += f". {data['author']}"
            if data.get("original_title"):
                title_parts.append(data["original_title"])
            title = "\n".join(title_parts)
            content = title
        else:
            title = data.get("title", text[:100]) or "Screenshot"
            content = data.get("content", text)
    except (_json.JSONDecodeError, AttributeError):
        title = text[:100] if text else "Screenshot"
        content = text

    return Item(
        title=title,
        content=content,
        raw_input=f"[screenshot: {image_path}]",
        item_type=ItemType.SCREENSHOT,
    )


async def _process_audio(audio_path: str) -> list[Item]:
    """Process audio — transcribe and extract tasks."""
    import json
    from ..services.transcriber import transcribe_audio
    from ..services.llm import VOICE_TO_TASKS_PROMPT, get_llm

    logger.info("Step 1/3: Transcribing audio...")
    transcription = await transcribe_audio(audio_path)
    logger.info(f"Transcription result ({len(transcription)} chars): {transcription[:200]}")

    if not transcription or not transcription.strip():
        logger.warning("Empty transcription, creating fallback item")
        return [Item(
            title="(empty voice message)",
            content="",
            raw_input="[empty transcription]",
            item_type=ItemType.VOICE,
        )]

    # Extract tasks from transcription
    logger.info("Step 2/3: Extracting tasks from transcription...")
    llm = get_llm()
    chain = VOICE_TO_TASKS_PROMPT | llm
    response = await chain.ainvoke({"transcription": transcription})
    logger.info(f"Task extraction response: {response.content[:500]}")

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
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"JSON parse failed: {e}")

    # Fallback: if no tasks extracted, save whole transcription as single item
    if not items:
        logger.info("No tasks extracted, saving transcription as single item")
        items.append(Item(
            title=transcription[:100],
            content=transcription,
            raw_input=transcription,
            item_type=ItemType.VOICE,
        ))

    logger.info(f"Extracted {len(items)} item(s) from voice")
    return items
