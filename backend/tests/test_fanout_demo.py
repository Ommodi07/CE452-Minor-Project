"""
Demonstrates the fan-out/fan-in mechanics end to end:

  planner -> Send() dispatches one researcher invocation per SubQuestion
          -> researchers run in parallel, each scoped to its own SubQuestion
          -> critic (static edge) only runs once all parallel branches finish
          -> source_docs / claims / errors accumulate via operator.add reducers

This test fixes the planner's output (rather than relying on its own
fallback) so we can control exactly how many sub-questions fan out, and with
which research_method each one carries — including a WEB_SEARCH/API/BOTH
mix, which is the case most likely to reveal fan-in bugs (different branches
producing different numbers of docs).
"""
from __future__ import annotations

import pytest

from app.graph import nodes as _nodes_pkg  # noqa: F401 (ensures package import works)
from app.graph.graph import get_compiled_graph
from app.graph.nodes import researcher as researcher_module
from app.graph.state import initial_state
from app.models.schemas import ResearchAngle, ResearchMethod, SubQuestion


def _fixed_sub_questions(query: str) -> list[SubQuestion]:
    return [
        SubQuestion(
            parent_query=query, question_text="factual angle question",
            angle=ResearchAngle.FACTUAL, research_method=ResearchMethod.WEB_SEARCH,
        ),
        SubQuestion(
            parent_query=query, question_text="current-status angle question",
            angle=ResearchAngle.CURRENT_STATUS, research_method=ResearchMethod.API,
        ),
        SubQuestion(
            parent_query=query, question_text="comparative angle question",
            angle=ResearchAngle.COMPARATIVE, research_method=ResearchMethod.BOTH,
        ),
    ]


@pytest.mark.asyncio
async def test_fan_out_dispatches_one_researcher_per_sub_question_and_merges_results(monkeypatch):
    query = "test fan-out query"

    async def fake_planner_node(state):
        return {"sub_questions": _fixed_sub_questions(query), "status": "researching"}

    call_log: list[str] = []

    async def fake_web_search(search_query, max_uses=4):
        call_log.append(f"web_search:{search_query}")
        return [{"url": f"https://example.com/{search_query[:10]}", "title": "T", "snippet": "s"}]

    async def fake_api_lookup(sub_question):
        call_log.append(f"api_lookup:{sub_question.question_text[:10]}")
        return [{"url": f"https://api.example.com/{sub_question.id}", "title": "API result", "snippet": "42"}]

    class _FakeLLMClient:
        is_configured = False  # forces the fallback claim-extraction path (no network needed)

    import app.graph.graph as graph_module

    monkeypatch.setattr(graph_module, "planner_node", fake_planner_node)
    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "api_lookup", fake_api_lookup)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _FakeLLMClient())

    # Graph is built fresh here (not the cached singleton) so the monkeypatched
    # planner_node is actually wired into the compiled graph's node table.
    graph = graph_module.build_graph().compile()

    start = initial_state(session_id="fanout-test", query=query, max_iterations=1)
    final_state = await graph.ainvoke(start)

    # 3 sub-questions dispatched in parallel via Send -> 3 researcher calls total.
    # WEB_SEARCH -> 1 web_search call. API -> 1 api_lookup call (succeeds, no web_search fallback).
    # BOTH -> both a web_search AND an api_lookup call.
    assert sum(c.startswith("web_search") for c in call_log) == 2  # WEB_SEARCH sub-question + BOTH sub-question
    assert sum(c.startswith("api_lookup") for c in call_log) == 2  # API sub-question + BOTH sub-question

    # Fan-in: source_docs/claims from all 3 parallel branches ended up merged
    # into one shared list (this is the operator.add reducer doing its job) —
    # not overwritten by whichever branch finished last.
    assert len(final_state["source_docs"]) == 4  # 1 + 1 + 2 (BOTH produces 2 docs)
    assert len(final_state["claims"]) == 4  # fallback path: 1 claim per doc with non-empty snippet

    sub_question_ids = {sq.id for sq in final_state["sub_questions"]}
    doc_sub_question_ids = {doc.sub_question_id for doc in final_state["source_docs"]}
    assert doc_sub_question_ids == sub_question_ids  # every branch's docs are attributed correctly

    assert final_state["status"] == "done"
    assert final_state["report"] is not None
