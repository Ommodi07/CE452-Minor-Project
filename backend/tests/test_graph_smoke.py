import pytest

from app.graph.graph import get_compiled_graph
from app.graph.state import initial_state


@pytest.mark.asyncio
async def test_graph_runs_end_to_end_with_placeholders(monkeypatch):
    graph = get_compiled_graph()
    start = initial_state(session_id="test-session", query="the impact of AI on hiring")

    async def fake_web_search(query, max_uses=4):
        return []

    class _FakeLLMClient:
        @property
        def is_configured(self):
            return False

    from app.graph.nodes import researcher as researcher_module

    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _FakeLLMClient())

    final_state = await graph.ainvoke(start, config={"configurable": {"thread_id": start["session_id"]}})

    assert final_state["status"] == "done"
    assert final_state["report"] is not None
    assert final_state["report"].session_id == "test-session"
    # No GEMINI_API_KEY in test env:
    # - planner falls back to its deterministic 4-sub-question set
    # - researcher's web_search is mocked to stay deterministic
    # The point of this test is that the graph still completes cleanly end
    # to end rather than crashing — failures are recorded, not swallowed.
    assert len(final_state["sub_questions"]) == 4
    assert final_state["source_docs"] == []
    assert final_state["claims"] == []
    assert len(final_state["errors"]) > 0
    assert all(
        ("GEMINI_API_KEY" in e) or ("web_search failed" in e) or ("no sources found" in e)
        for e in final_state["errors"]
    )
    # Unanswered sub-questions should show up as report limitations, not be silently dropped.
    assert len(final_state["report"].limitations) == 4
