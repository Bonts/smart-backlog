"""Book search service — find links on Open Library and Google Books."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10
_USER_AGENT = "SmartBacklogBot (github.com/Bonts/smart-backlog)"


async def search_book_links(title: str, author: str = "") -> dict[str, str]:
    """Search for book links on Open Library and Google Books.

    Returns dict with keys like:
        "read"   — free reading link (Open Library / archive.org)
        "info"   — info page (Open Library or Google Books)
        "buy"    — Google Books preview/buy link
    """
    links: dict[str, str] = {}

    # 1. Open Library — free reading + info
    ol = await _search_open_library(title, author)
    if ol:
        links.update(ol)

    # 2. Google Books — preview/buy
    gb = await _search_google_books(title, author)
    if gb:
        links.update(gb)

    return links


async def _search_open_library(title: str, author: str) -> dict[str, str]:
    """Search Open Library for a book."""
    try:
        query = title
        if author:
            query += f" {author}"
        url = f"https://openlibrary.org/search.json?q={quote_plus(query)}&limit=1&fields=key,title,author_name,edition_key,ia"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers={"User-Agent": _USER_AGENT})
            resp.raise_for_status()
            data = resp.json()

        docs = data.get("docs", [])
        if not docs:
            return {}

        doc = docs[0]
        result: dict[str, str] = {}

        # Info page
        work_key = doc.get("key", "")
        if work_key:
            result["info"] = f"https://openlibrary.org{work_key}"

        # Free reading via Internet Archive
        ia_ids = doc.get("ia", [])
        if ia_ids:
            result["read"] = f"https://archive.org/details/{ia_ids[0]}"

        return result
    except Exception as e:
        logger.debug(f"Open Library search failed: {e}")
        return {}


async def _search_google_books(title: str, author: str) -> dict[str, str]:
    """Search Google Books for a book."""
    try:
        query = f"intitle:{title}"
        if author:
            query += f"+inauthor:{author}"
        url = f"https://www.googleapis.com/books/v1/volumes?q={quote_plus(query)}&maxResults=1"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers={"User-Agent": _USER_AGENT})
            resp.raise_for_status()
            data = resp.json()

        items = data.get("items", [])
        if not items:
            return {}

        volume = items[0].get("volumeInfo", {})
        result: dict[str, str] = {}

        # Google Books preview link
        preview = volume.get("previewLink", "")
        if preview:
            result["buy"] = preview

        # If there's a free epub/pdf
        access = items[0].get("accessInfo", {})
        if access.get("epub", {}).get("isAvailable") or access.get("pdf", {}).get("isAvailable"):
            if not result.get("read"):
                result["read"] = preview

        return result
    except Exception as e:
        logger.debug(f"Google Books search failed: {e}")
        return {}
