"""
Tests for the reflection loop: Critic flagging a sub-question whose claims
are too heavily Unverified/Disputed, generating a refined search query, and
that query actually reaching Researcher on the retry pass.
"""
from __future__ import annotations

import pytest

from app.graph.nodes import critic as critic_module
from app.graph.nodes import researcher as researcher_module
from app.models.schemas import ResearchAngle, ResearchMethod, SourceDoc, SubQuestion, VerificationStatus


def _doc(url, sub_question_id, snippet="content", credibility_score=0.8):
    return SourceDoc(
        sub_question_id=sub_question_id, url=url, title=url, snippet=snippet, credibility_score=credibility_score,
    )


def _sub_question(text="q") -> SubQuestion:
    return SubQuestion(
        parent_query="test", question_text=text,
        angle=ResearchAngle.FACTUAL, research_method=ResearchMethod.WEB_SEARCH,
    )


class _FakeLLMClient:
    def __init__(self, evidence=None, refined_query="a more targeted query", refine_should_raise=False):
        self._evidence = evidence or []
        self._refined_query = refined_query
        self._refine_should_raise = refine_should_raise

    is_configured = True

    async def extract_and_verify_claims(self, *, source_docs, system_prompt, user_prompt):
        return self._evidence

    async def refine_search_query(self, *, sub_question, problematic_claims, system_prompt, user_prompt):
        if self._refine_should_raise:
            raise RuntimeError("simulated refinement failure")
        return self._refined_query


@pytest.mark.asyncio
async def test_reflection_triggers_when_ratio_exceeds_threshold(monkeypatch):
    sub_question = _sub_question("disputed topic")
    doc_a = _doc("https://a.com/1", sub_question.id)
    doc_b = _doc("https://b.com/1", sub_question.id)

    # 1 disputed claim out of 1 total -> ratio 1.0, well over the 0.5 threshold.
    evidence = [
        {
            "claim_text": "Conflicting figures reported",
            "primary_source_url": doc_a.url,
            "supporting_source_urls": [],
            "contradicting_source_urls": [doc_b.url],
            "critic_notes": "sources disagree on the number",
        }
    ]
    monkeypatch.setattr(critic_module, "build_llm_client", lambda: _FakeLLMClient(evidence))

    state = {
        "source_docs": [doc_a, doc_b],
        "sub_questions": [sub_question],
        "claims": [],
        "iteration_count": 0,
        "max_iterations": 3,
    }
    result = await critic_module.critic_node(state)

    assert sub_question.question_text in result["open_questions"]
    updated_sq = result["sub_questions"][0]
    assert updated_sq.refined_query == "a more targeted query"
    assert updated_sq.id == sub_question.id  # same sub-question, not a new one


@pytest.mark.asyncio
async def test_reflection_not_triggered_when_below_threshold(monkeypatch):
    sub_question = _sub_question("well-covered topic")
    doc_a = _doc("https://a.com/1", sub_question.id)
    doc_b = _doc("https://b.com/1", sub_question.id)
    doc_c = _doc("https://c.com/1", sub_question.id)

    # 1 unverified out of 3 (0.33 ratio) -> below the 0.5 threshold.
    evidence = [
        {"claim_text": "Corroborated claim 1", "primary_source_url": doc_a.url,
         "supporting_source_urls": [doc_b.url], "contradicting_source_urls": [], "critic_notes": ""},
        {"claim_text": "Corroborated claim 2", "primary_source_url": doc_b.url,
         "supporting_source_urls": [doc_a.url], "contradicting_source_urls": [], "critic_notes": ""},
        {"claim_text": "Unverified claim", "primary_source_url": doc_c.url,
         "supporting_source_urls": [], "contradicting_source_urls": [], "critic_notes": ""},
    ]
    monkeypatch.setattr(critic_module, "build_llm_client", lambda: _FakeLLMClient(evidence))

    state = {
        "source_docs": [doc_a, doc_b, doc_c],
        "sub_questions": [sub_question],
        "claims": [],
        "iteration_count": 0,
        "max_iterations": 3,
    }
    result = await critic_module.critic_node(state)

    assert sub_question.question_text not in result["open_questions"]
    assert result["sub_questions"][0].refined_query is None


@pytest.mark.asyncio
async def test_reflection_query_generation_skipped_at_iteration_cap(monkeypatch):
    """If this is the last allowed iteration, don't bother generating a refined
    query (it'll never be used) — route_after_critic will send straight to writer."""
    sub_question = _sub_question("disputed topic")
    doc_a = _doc("https://a.com/1", sub_question.id)
    doc_b = _doc("https://b.com/1", sub_question.id)

    evidence = [
        {"claim_text": "Conflicting claim", "primary_source_url": doc_a.url,
         "supporting_source_urls": [], "contradicting_source_urls": [doc_b.url], "critic_notes": ""},
    ]

    call_count = {"refine": 0}

    class _CountingLLMClient(_FakeLLMClient):
        async def refine_search_query(self, **kwargs):
            call_count["refine"] += 1
            return await super().refine_search_query(**kwargs)

    monkeypatch.setattr(critic_module, "build_llm_client", lambda: _CountingLLMClient(evidence))

    state = {
        "source_docs": [doc_a, doc_b],
        "sub_questions": [sub_question],
        "claims": [],
        "iteration_count": 1,
        "max_iterations": 2,  # iteration_count+1 (2) is NOT < max_iterations (2) -> no more looping
    }
    result = await critic_module.critic_node(state)

    assert call_count["refine"] == 0  # refinement call skipped — would be wasted
    assert result["sub_questions"][0].refined_query is None
    # still correctly flagged as an open question / limitation, just no wasted refinement
    assert sub_question.question_text in result["open_questions"]


@pytest.mark.asyncio
async def test_reflection_falls_back_to_heuristic_query_on_llm_failure(monkeypatch):
    sub_question = _sub_question("disputed topic")
    doc_a = _doc("https://a.com/1", sub_question.id)
    doc_b = _doc("https://b.com/1", sub_question.id)

    evidence = [
        {"claim_text": "Conflicting claim", "primary_source_url": doc_a.url,
         "supporting_source_urls": [], "contradicting_source_urls": [doc_b.url], "critic_notes": ""},
    ]
    monkeypatch.setattr(
        critic_module, "build_llm_client", lambda: _FakeLLMClient(evidence, refine_should_raise=True)
    )

    state = {
        "source_docs": [doc_a, doc_b],
        "sub_questions": [sub_question],
        "claims": [],
        "iteration_count": 0,
        "max_iterations": 3,
    }
    result = await critic_module.critic_node(state)

    refined = result["sub_questions"][0].refined_query
    assert refined is not None
    assert "reconcile conflicting reports" in refined  # the disputed-path fallback heuristic


@pytest.mark.asyncio
async def test_researcher_uses_refined_query_when_present(monkeypatch):
    sub_question = _sub_question("original phrasing")
    sub_question = sub_question.model_copy(update={"refined_query": "a much better phrasing"})

    captured_queries = []

    async def fake_web_search(query, max_uses=4):
        captured_queries.append(query)
        return [{"url": "https://example.com/a", "title": "A", "snippet": "s"}]

    class _Unconfigured:
        is_configured = False

    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _Unconfigured())

    await researcher_module.researcher_node({"active_sub_question": sub_question})

    assert captured_queries == ["a much better phrasing"]


@pytest.mark.asyncio
async def test_researcher_uses_question_text_when_no_refined_query(monkeypatch):
    sub_question = _sub_question("original phrasing")

    captured_queries = []

    async def fake_web_search(query, max_uses=4):
        captured_queries.append(query)
        return [{"url": "https://example.com/a", "title": "A", "snippet": "s"}]

    class _Unconfigured:
        is_configured = False

    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _Unconfigured())

    await researcher_module.researcher_node({"active_sub_question": sub_question})

    assert captured_queries == ["original phrasing"]
