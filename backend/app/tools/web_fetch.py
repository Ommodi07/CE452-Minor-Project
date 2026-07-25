"""Placeholder page-fetch tool. Wire up to an HTTP client + HTML->text extraction."""
from __future__ import annotations


async def web_fetch(url: str) -> str:
    raise NotImplementedError("Wire this up to an HTTP client + content extraction.")
