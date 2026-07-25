"""
Researcher node.

One invocation handles ONE SubQuestion (fanned out via Send — see
app/graph/routing.py). Two phases:

  1. Gather sources — dispatches to web_search and/or api_lookup depending
     on `sub_question.research_method`, producing SourceDocs.
  2. Extract claims — turns those SourceDocs into Claims via the LLM.

Both phases degrade gracefully rather than raising: a failed/unavailable
tool or LLM call is recorded in `state["errors"]` and the node still
returns a (possibly empty or partially-filled) result, so one bad
sub-question can't crash the whole parallel fan-out.
"""
from __future__ import annotations

import logging
import re

from app.graph.prompts.researcher import CLAIM_SYSTEM_PROMPT, build_claim_extraction_prompt
from app.graph.state import GraphState
from app.models.schemas import Claim, ResearchMethod, SourceDoc, SourceType, SubQuestion
from app.services.llm_client import build_llm_client
from app.tools.api_lookup import api_lookup
from app.tools.dedup import dedupe_source_docs
from app.tools.quality import assess_source_quality
from app.tools.vector_store import get_vector_store
from app.tools.web_search import web_search

logger = logging.getLogger(__name__)

_ACADEMIC_PATTERNS = (".edu", "arxiv.org", "ncbi.nlm.nih.gov", "nature.com", "sciencedirect.com")
_GOV_PATTERNS = (".gov", ".mil")
_NEWS_PATTERNS = (
    "reuters.com", "apnews.com", "bloomberg.com", "nytimes.com", "wsj.com",
    "bbc.co", "theguardian.com", "ft.com", "npr.org",
)
_BLOG_PATTERNS = ("medium.com", "substack.com", "blogspot.", "wordpress.com")


def _infer_source_type(url: str) -> SourceType:
    """Cheap domain-pattern heuristic. Swap for a real classifier if credibility scoring matters."""
    url_lower = url.lower()
    if any(p in url_lower for p in _GOV_PATTERNS):
        return SourceType.GOV
    if any(p in url_lower for p in _ACADEMIC_PATTERNS):
        return SourceType.ACADEMIC
    if any(p in url_lower for p in _NEWS_PATTERNS):
        return SourceType.NEWS
    if any(p in url_lower for p in _BLOG_PATTERNS):
        return SourceType.BLOG
    return SourceType.OTHER


def _fallback_claims(source_docs: list[SourceDoc], sub_question: SubQuestion) -> list[Claim]:
    """Naive 1-claim-per-doc fallback used when the LLM isn't available for extraction."""
    claims = []
    for doc in source_docs:
        if not doc.snippet:
            continue
        claims.append(
            Claim(
                source_doc_id=doc.id,
                sub_question_id=sub_question.id,
                claim_text=re.sub(r"\s+", " ", doc.snippet).strip()[:280],
                confidence=0.4,  # low-confidence: unverified heuristic extraction, not LLM-reasoned
                supporting_excerpt=doc.snippet,
            )
        )
    return claims


async def _gather_source_docs(sub_question: SubQuestion) -> tuple[list[SourceDoc], list[str]]:
    """Phase 1: dispatch to web_search / api_lookup per research_method. Returns (docs, error_notes)."""
    errors: list[str] = []
    raw_results: list[dict] = []

    if sub_question.research_method in (ResearchMethod.API, ResearchMethod.BOTH):
        try:
            api_results = await api_lookup(sub_question)
        except Exception as exc:  # noqa: BLE001
            logger.warning("api_lookup failed for sub_question=%s: %s", sub_question.id, exc)
            errors.append(f"researcher: api_lookup failed for '{sub_question.question_text}': {exc}")
            api_results = None

        if api_results:
            raw_results.extend(api_results)
        elif sub_question.research_method == ResearchMethod.API:
            errors.append(
                f"researcher: no API provider registered for '{sub_question.question_text}', "
                "falling back to web search"
            )

    # web_search runs whenever method is WEB_SEARCH/BOTH, or when API was requested
    # but no provider matched (better a degraded answer than none).
    needs_web_search = (
        sub_question.research_method in (ResearchMethod.WEB_SEARCH, ResearchMethod.BOTH)
        or not raw_results
    )
    if needs_web_search:
        # A refined_query means this is a reflection-loop retry (see
        # critic_node) — the sub-question's meaning hasn't changed, but the
        # Critic decided the original phrasing wasn't finding good enough
        # sources, so search with its more targeted follow-up query instead.
        search_query = sub_question.refined_query or sub_question.question_text
        if sub_question.refined_query:
            logger.info(
                "researcher: using refined query for sub_question=%s: %r",
                sub_question.id, search_query,
            )
        try:
            raw_results.extend(await web_search(search_query))
        except Exception as exc:  # noqa: BLE001
            logger.warning("web_search failed for sub_question=%s: %s", sub_question.id, exc)
            errors.append(f"researcher: web_search failed for '{sub_question.question_text}': {exc}")

    source_docs = [
        SourceDoc(
            sub_question_id=sub_question.id,
            url=r["url"],
            title=r.get("title") or r["url"],
            snippet=r.get("snippet", ""),
            source_type=_infer_source_type(r["url"]),
            published_date=r.get("page_age"),
        )
        for r in raw_results
        if r.get("url")
    ]

    deduped_count = len(source_docs)
    source_docs = dedupe_source_docs(source_docs)
    if len(source_docs) < deduped_count:
        logger.info(
            "researcher: deduped %d duplicate source(s) for sub_question=%s",
            deduped_count - len(source_docs),
            sub_question.id,
        )

    for doc in source_docs:
        quality_flags, credibility_score = assess_source_quality(doc)
        doc.quality_flags = quality_flags
        doc.credibility_score = credibility_score

    vector_store = get_vector_store()
    if vector_store is not None:
        for doc in source_docs:
            try:
                await vector_store.upsert(
                    doc.id,
                    f"{doc.title}\n\n{doc.snippet}".strip(),
                    metadata={
                        "url": doc.url,
                        "title": doc.title,
                        "sub_question_id": doc.sub_question_id,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("vector store upsert failed for doc_id=%s: %s", doc.id, exc)

    return source_docs, errors


async def researcher_node(state: GraphState) -> dict:
    sub_question: SubQuestion = state["active_sub_question"]  # type: ignore[typeddict-item]
    errors: list[str] = []

    source_docs, gather_errors = await _gather_source_docs(sub_question)
    errors.extend(gather_errors)

    if not source_docs:
        errors.append(f"researcher: no sources found for sub-question '{sub_question.question_text}'")
        result: dict = {"source_docs": [], "claims": []}
        if errors:
            result["errors"] = errors
        return result

    llm_client = build_llm_client()
    if llm_client.is_configured:
        try:
            claims = await llm_client.extract_claims(
                sub_question=sub_question,
                source_docs=source_docs,
                system_prompt=CLAIM_SYSTEM_PROMPT,
                user_prompt=build_claim_extraction_prompt(sub_question, source_docs),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("extract_claims failed for sub_question=%s: %s", sub_question.id, exc)
            errors.append(f"researcher: claim extraction failed, used fallback claims ({exc})")
            claims = _fallback_claims(source_docs, sub_question)
    else:
        claims = _fallback_claims(source_docs, sub_question)

    result = {"source_docs": source_docs, "claims": claims}
    if errors:
        result["errors"] = errors
    return result
