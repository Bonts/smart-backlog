"""URL title and metadata extraction."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup


async def extract_url_title(url: str) -> str:
    """Fetch URL and extract page title."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        response = await client.get(url, headers={"User-Agent": "SmartBacklog/1.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else url
