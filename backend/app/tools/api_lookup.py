"""
Pluggable registry for structured/API data sources.

"Any relevant APIs" is inherently project-specific (stock prices, weather,
sports scores, gov statistics, internal company data, ...), so rather than
hardcoding one provider, this is a thin registry: register a keyword ->
async provider function, and `api_lookup` dispatches to the first provider
whose keyword appears in the sub-question text.

No providers are registered by default. Register your own, e.g.:

    from app.tools.api_lookup import register_provider

    async def stock_price_provider(sub_question: SubQuestion) -> list[dict]:
        # call a real market-data API here
        return [{"url": "https://api.example.com/quote/AAPL", "title": "AAPL quote", "snippet": "..."}]

    register_provider("stock price", stock_price_provider)

If no registered keyword matches, `api_lookup` returns None and the caller
(researcher_node) falls back to web_search rather than silently producing
no sources.
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from app.models.schemas import SubQuestion

logger = logging.getLogger(__name__)

ApiProvider = Callable[[SubQuestion], Awaitable[list[dict]]]

_REGISTRY: dict[str, ApiProvider] = {}


def register_provider(keyword: str, provider: ApiProvider) -> None:
    """Register `provider` to handle sub-questions containing `keyword` (case-insensitive)."""
    _REGISTRY[keyword.lower()] = provider


async def api_lookup(sub_question: SubQuestion) -> list[dict] | None:
    """
    Return structured results for `sub_question` if a matching provider is
    registered, else None (meaning: no structured source available for this
    question — the caller should fall back to web_search).
    """
    question_lower = sub_question.question_text.lower()
    for keyword, provider in _REGISTRY.items():
        if keyword in question_lower:
            try:
                return await provider(sub_question)
            except Exception:
                logger.exception("API provider for keyword '%s' failed", keyword)
                return None
    return None
