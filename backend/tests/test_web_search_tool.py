"""Tests the DuckDuckGo-backed parsing logic in app/tools/web_search.py."""
from __future__ import annotations

import pytest

from app.tools import web_search as web_search_module


class _FakeDDGS:
    def __init__(self, results):
        self._results = results

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def text(self, query, max_results=4, safesearch="moderate"):
        return list(self._results)


@pytest.mark.asyncio
async def test_web_search_merges_page_age_from_tool_result_with_citation_text(monkeypatch):
    fake_results = [
        {
            "href": "https://example.com/a",
            "title": "Example A",
            "body": "X happened in 2026.",
            "date": "April 30, 2025",
        },
        {
            "href": "https://example.com/never-cited",
            "title": "Uncited page",
            "body": "",
            "date": "6 days ago",
        },
    ]

    monkeypatch.setattr(web_search_module, "DDGS", lambda: _FakeDDGS(fake_results))

    results = await web_search_module.web_search("test query")

    by_url = {r["url"]: r for r in results}
    assert by_url["https://example.com/a"]["page_age"] == "April 30, 2025"
    assert "X happened in 2026." in by_url["https://example.com/a"]["snippet"]
    # Uncited page still shows up (with page_age) even though it has no snippet.
    assert by_url["https://example.com/never-cited"]["page_age"] == "6 days ago"
    assert by_url["https://example.com/never-cited"]["snippet"] == ""


@pytest.mark.asyncio
async def test_web_search_returns_empty_list_when_nothing_cited(monkeypatch):
    monkeypatch.setattr(web_search_module, "DDGS", lambda: _FakeDDGS([]))

    results = await web_search_module.web_search("test query")
    assert results == []
