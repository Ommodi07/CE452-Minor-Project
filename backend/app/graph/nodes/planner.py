"""
Planner node.

Decomposes `original_query` into 4-6 SubQuestions, each tagged with:
  - `angle`            (factual / current_status / causal / comparative /
                         risk_controversy / stakeholder / forecast)
  - `research_method`  (web_search / api / both)

Calls the LLM via `LLMClient.generate_sub_questions`, which forces a
structured JSON response so the output is schema-conformant. If the client isn't
configured (no GEMINI_API_KEY) or the call fails/returns something
invalid, falls back to a deterministic set of sub-questions so the graph
can still run end-to-end — the failure is recorded in `state["errors"]`
rather than silently swallowed.

This is also the node a Critic-triggered full replan routes back to.
"""
from __future__ import annotations

import logging

from app.graph.prompts.planner import (
    MAX_SUB_QUESTIONS,
    MIN_SUB_QUESTIONS,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.graph.state import GraphState
from app.models.schemas import ResearchAngle, ResearchMethod, SubQuestion
from app.services.llm_client import build_llm_client

logger = logging.getLogger(__name__)


def _fallback_sub_questions(query: str) -> list[SubQuestion]:
    """
    Deterministic, angle-diverse sub-questions used when the LLM call isn't
    available or fails. Keeps the graph runnable (e.g. in local dev without
    an API key, or in CI) rather than hard-failing the whole run.
    """
    fallback_specs = [
        (ResearchAngle.FACTUAL, ResearchMethod.WEB_SEARCH,
         f"What are the key facts and background needed to understand: {query}?"),
        (ResearchAngle.CURRENT_STATUS, ResearchMethod.WEB_SEARCH,
         f"What is the current state of: {query}?"),
        (ResearchAngle.CAUSAL, ResearchMethod.WEB_SEARCH,
         f"What factors are driving or causing: {query}?"),
        (ResearchAngle.RISK_CONTROVERSY, ResearchMethod.WEB_SEARCH,
         f"What are the key risks, criticisms, or controversies around: {query}?"),
    ]
    return [
        SubQuestion(
            parent_query=query,
            question_text=text,
            rationale="Fallback sub-question generated without LLM access.",
            angle=angle,
            research_method=method,
            priority=1,
        )
        for angle, method, text in fallback_specs
    ]


def _clamp_and_dedupe(sub_questions: list[SubQuestion], query: str) -> list[SubQuestion]:
    """Enforce the 4-6 count contract even if the model over/under-delivers."""
    seen_text: set[str] = set()
    deduped: list[SubQuestion] = []
    for sq in sub_questions:
        key = sq.question_text.strip().lower()
        if key and key not in seen_text:
            seen_text.add(key)
            deduped.append(sq)

    if len(deduped) > MAX_SUB_QUESTIONS:
        # Keep the highest-priority (lowest number) ones, stable on original order.
        deduped = sorted(deduped, key=lambda sq: sq.priority)[:MAX_SUB_QUESTIONS]

    if len(deduped) < MIN_SUB_QUESTIONS:
        existing_angles = {sq.angle for sq in deduped}
        for filler in _fallback_sub_questions(query):
            if len(deduped) >= MIN_SUB_QUESTIONS:
                break
            if filler.angle not in existing_angles:
                deduped.append(filler)
                existing_angles.add(filler.angle)

    return deduped


async def planner_node(state: GraphState) -> dict:
    query = state["original_query"]
    llm_client = build_llm_client()
    errors: list[str] = []

    if llm_client.is_configured:
        try:
            sub_questions = await llm_client.generate_sub_questions(
                query=query,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(query),
            )
        except Exception as exc:  # noqa: BLE001 - degrade gracefully, don't crash the run
            logger.warning("Planner LLM call failed, using fallback sub-questions: %s", exc)
            errors.append(f"planner: LLM call failed, used fallback sub-questions ({exc})")
            sub_questions = _fallback_sub_questions(query)
    else:
        logger.info("Planner: GEMINI_API_KEY not configured, using fallback sub-questions.")
        sub_questions = _fallback_sub_questions(query)

    sub_questions = _clamp_and_dedupe(sub_questions, query)

    result: dict = {
        "sub_questions": sub_questions,
        "status": "researching",
    }
    if errors:
        result["errors"] = errors
    return result
