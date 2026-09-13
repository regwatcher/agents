"""Fetch and extract readable text from a URL (CrewAI ScrapeWebsiteTool analogue)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import requests
from agents import function_tool
from bs4 import BeautifulSoup


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@function_tool
def scrape_website(url: str, max_chars: int = 24000) -> str:
    """Fetch a web page and return main text content (HTML stripped). Use for non-LinkedIn pages."""
    raw = (url or "").strip()
    if not raw:
        return "Error: empty URL"

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    if parsed.scheme not in ("http", "https"):
        return "Error: URL must be http or https"

    try:
        r = requests.get(
            raw if "://" in raw else f"https://{raw}",
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; RecruitmentAgents/1.0; "
                    "+https://example.com/bot)"
                ),
            },
        )
        r.raise_for_status()
    except requests.RequestException as e:
        return f"Error fetching URL: {e!s}"

    soup = BeautifulSoup(r.content, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    text = _normalize_whitespace(soup.get_text(separator="\n"))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n… [truncated]"
    return text or "(No extractable text)"
