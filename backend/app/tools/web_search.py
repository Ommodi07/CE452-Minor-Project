"""Web search backed by DuckDuckGo results.

This keeps the researcher node functional without a vendor-specific hosted
search tool. The caller still receives the same url/title/snippet/page_age
shape used elsewhere in the pipeline.
"""
from __future__ import annotations

import asyncio
import logging

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


async def web_search(query: str, max_uses: int = 4) -> list[dict]:
    """Return readable search results as url/title/snippet/page_age dicts."""

    def _search() -> list[dict]:
        results: dict[str, dict] = {}
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_uses, safesearch="moderate"):
                url = item.get("href") or item.get("url")
                if not url:
                    continue

                entry = results.get(url)
                if entry is None:
                    entry = {
                        "url": url,
                        "title": item.get("title") or url,
                        "snippet": item.get("body") or item.get("snippet") or "",
                        "page_age": item.get("date"),
                    }
                    results[url] = entry
                else:
                    if item.get("title") and entry["title"] == entry["url"]:
                        entry["title"] = item["title"]
                    snippet = item.get("body") or item.get("snippet") or ""
                    if snippet and snippet not in entry["snippet"]:
                        entry["snippet"] = f"{entry['snippet']} {snippet}".strip()
                    if item.get("date") and not entry.get("page_age"):
                        entry["page_age"] = item["date"]

        return list(results.values())

    try:
        return await asyncio.to_thread(_search)
    except Exception as exc:  # noqa: BLE001
        logger.warning("web_search failed for query=%r: %s", query, exc)
        raise