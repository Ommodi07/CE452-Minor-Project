import pytest

from app.graph.nodes import planner as planner_module
from app.models.schemas import ResearchAngle, ResearchMethod, SubQuestion


class _FakeLLMClient:
    """Stand-in for LLMClient so tests don't hit the real Gemini API."""

    def __init__(self, sub_questions=None, should_raise: bool = False):
        self._sub_questions = sub_questions or []
        self._should_raise = should_raise

    @property
    def is_configured(self) -> bool:
        return True

    async def generate_sub_questions(self, *, query, system_prompt, user_prompt):
        if self._should_raise:
            raise RuntimeError("simulated model failure")
        return self._sub_questions


def _sq(query: str, text: str, angle: ResearchAngle, method: ResearchMethod, priority: int = 1) -> SubQuestion:
    return SubQuestion(
        parent_query=query,
        question_text=text,
        rationale="test rationale",
        angle=angle,
        research_method=method,
        priority=priority,
    )


@pytest.mark.asyncio
async def test_planner_uses_llm_output_when_within_bounds(monkeypatch):
    query = "the impact of remote work on urban housing prices"
    llm_output = [
        _sq(query, "What is remote work and how prevalent is it?", ResearchAngle.FACTUAL, ResearchMethod.WEB_SEARCH),
        _sq(query, "What is the current state of urban housing prices?", ResearchAngle.CURRENT_STATUS, ResearchMethod.API),
        _sq(query, "Why might remote work affect housing demand?", ResearchAngle.CAUSAL, ResearchMethod.WEB_SEARCH),
        _sq(query, "How does this compare to prior migration-driven housing shifts?", ResearchAngle.COMPARATIVE, ResearchMethod.WEB_SEARCH),
        _sq(query, "What controversies exist around this claim?", ResearchAngle.RISK_CONTROVERSY, ResearchMethod.WEB_SEARCH),
    ]
    monkeypatch.setattr(planner_module, "build_llm_client", lambda: _FakeLLMClient(llm_output))

    result = await planner_module.planner_node({"original_query": query})

    assert result["status"] == "researching"
    assert "errors" not in result
    assert len(result["sub_questions"]) == 5
    assert result["sub_questions"] == llm_output


@pytest.mark.asyncio
async def test_planner_clamps_to_max_when_llm_returns_too_many(monkeypatch):
    query = "quantum computing commercial viability"
    llm_output = [
        _sq(query, f"Sub-question {i}", ResearchAngle.FACTUAL, ResearchMethod.WEB_SEARCH, priority=i % 3 + 1)
        for i in range(9)
    ]
    monkeypatch.setattr(planner_module, "build_llm_client", lambda: _FakeLLMClient(llm_output))

    result = await planner_module.planner_node({"original_query": query})

    assert len(result["sub_questions"]) == planner_module.MAX_SUB_QUESTIONS


@pytest.mark.asyncio
async def test_planner_pads_when_llm_returns_too_few(monkeypatch):
    query = "the future of nuclear energy in Europe"
    llm_output = [
        _sq(query, "Only one sub-question", ResearchAngle.FACTUAL, ResearchMethod.WEB_SEARCH),
    ]
    monkeypatch.setattr(planner_module, "build_llm_client", lambda: _FakeLLMClient(llm_output))

    result = await planner_module.planner_node({"original_query": query})

    assert len(result["sub_questions"]) >= planner_module.MIN_SUB_QUESTIONS


@pytest.mark.asyncio
async def test_planner_falls_back_on_llm_exception(monkeypatch):
    query = "effects of tariffs on semiconductor supply chains"
    monkeypatch.setattr(planner_module, "build_llm_client", lambda: _FakeLLMClient(should_raise=True))

    result = await planner_module.planner_node({"original_query": query})

    assert len(result["sub_questions"]) >= planner_module.MIN_SUB_QUESTIONS
    assert "errors" in result
    assert "fallback" in result["errors"][0]


@pytest.mark.asyncio
async def test_planner_does_not_pad_a_well_formed_simple_query(monkeypatch):
    """
    Regression guard: a narrow factual query answered with 2 well-formed,
    genuinely-different-angle sub-questions should NOT be padded up to 4+
    with manufactured comparative/stakeholder angles. This is the exact
    failure mode found when testing "boiling point of nitrogen"-style
    queries against the v1 prompt.
    """
    query = "What is the boiling point of nitrogen at sea level?"
    llm_output = [
        _sq(query, "What is the boiling point of nitrogen at standard atmospheric pressure?", ResearchAngle.FACTUAL, ResearchMethod.WEB_SEARCH, priority=1),
        _sq(query, "Has the standard reference pressure used for this value changed recently?", ResearchAngle.CURRENT_STATUS, ResearchMethod.WEB_SEARCH, priority=2),
    ]
    monkeypatch.setattr(planner_module, "build_llm_client", lambda: _FakeLLMClient(llm_output))

    result = await planner_module.planner_node({"original_query": query})

    assert len(result["sub_questions"]) == 2
    assert result["sub_questions"] == llm_output


@pytest.mark.asyncio
async def test_planner_falls_back_when_not_configured(monkeypatch):
    query = "state of AI regulation in the EU"

    class _Unconfigured:
        is_configured = False

    monkeypatch.setattr(planner_module, "build_llm_client", lambda: _Unconfigured())

    result = await planner_module.planner_node({"original_query": query})

    assert planner_module.MIN_SUB_QUESTIONS <= len(result["sub_questions"]) <= planner_module.MAX_SUB_QUESTIONS
    angles = {sq.angle for sq in result["sub_questions"]}
    assert len(angles) > 1  # genuinely different angles, not duplicates
