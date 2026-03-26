"""Test the processing pipeline — URL extraction and text handling (no LLM needed)."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.models import Item, ItemType
from src.services.web_scraper import extract_url_title


async def test_url_extraction():
    """Test that we can extract a title from a URL."""
    url = "https://docs.python.org/3/"
    title = await extract_url_title(url)
    print(f"[OK] URL title extracted: '{title}'")
    assert len(title) > 0


async def test_url_pattern_detection():
    """Test URL pattern detection from processor."""
    from src.core.processor import URL_PATTERN

    assert URL_PATTERN.match("https://example.com")
    assert URL_PATTERN.match("http://docs.python.org/3/")
    assert not URL_PATTERN.match("just some text")
    assert not URL_PATTERN.match("not a url at all")
    print("[OK] URL pattern detection works")


async def test_text_item_creation():
    """Test creation of a text item (without AI categorization)."""
    item = Item(
        title="Fix the login bug",
        content="Users report 500 error on /api/login when password contains special chars",
        item_type=ItemType.NOTE,
    )
    assert item.id is not None
    assert item.title == "Fix the login bug"
    assert item.item_type == ItemType.NOTE
    print(f"[OK] Text item created: {item.id}")


async def main():
    await test_url_pattern_detection()
    await test_text_item_creation()
    await test_url_extraction()
    print("\n=== ALL PIPELINE TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
