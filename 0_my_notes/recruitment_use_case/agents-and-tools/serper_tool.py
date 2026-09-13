"""Serper.dev Google Search as an OpenAI Agents function_tool."""

from __future__ import annotations

import os
from typing import Any

import requests
from agents import function_tool


@function_tool
def serper_search(query: str, num_results: int = 12) -> list[dict[str, Any]]:
    """Search Google via Serper API. Prefer queries like ``site:linkedin.com/in keywords``."""
    api_key = os.getenv("SERPER_API_KEY") or ""
    if not api_key.strip():
        return [{"error": "SERPER_API_KEY is not set"}]

    r = requests.post(
        "https://google.serper.dev/search",
        headers={
            "X-API-KEY": api_key.strip(),
            "Content-Type": "application/json",
        },
        json={"q": query, "num": min(max(num_results, 1), 20)},
        timeout=30,
    )
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        return [{"error": str(e), "body": r.text[:500]}]

    data = r.json()
    organic = data.get("organic") or []
    out: list[dict[str, Any]] = []
    for h in organic[:num_results]:
        out.append(
            {
                "title": h.get("title"),
                "link": h.get("link"),
                "snippet": h.get("snippet"),
            }
        )
    return out
