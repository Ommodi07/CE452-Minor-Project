import pytest

from app.graph.nodes import researcher as researcher_module
from app.models.schemas import ResearchAngle, ResearchMethod, SourceType, SubQuestion


def _sub_question(method: ResearchMethod, text: str = "What is the current state of X?") -> SubQuestion:
    return SubQuestion(
        parent_query="test query",
        question_text=text,
        angle=ResearchAngle.CURRENT_STATUS,
        research_method=method,
    )


class _FakeLLMClient:
    def __init__(self, claims=None, should_raise=False, configured=True):
        self._claims = claims or []
        self._should_raise = should_raise
        self._configured = configured

    @property
    def is_configured(self):
        return self._configured

    async def extract_claims(self, *, sub_question, source_docs, system_prompt, user_prompt):
        if self._should_raise:
            raise RuntimeError("simulated extraction failure")
        return self._claims


@pytest.mark.asyncio
async def test_web_search_method_calls_web_search_only(monkeypatch):
    sub_question = _sub_question(ResearchMethod.WEB_SEARCH)

    async def fake_web_search(query, max_uses=4):
        return [{"url": "https://example.com/a", "title": "A", "snippet": "some fact about X"}]

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("api_lookup should not be called for WEB_SEARCH method")

    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "api_lookup", fail_if_called)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _FakeLLMClient())

    result = await researcher_module.researcher_node({"active_sub_question": sub_question})

    assert len(result["source_docs"]) == 1
    assert result["source_docs"][0].url == "https://example.com/a"
    assert result["source_docs"][0].source_type == SourceType.OTHER


@pytest.mark.asyncio
async def test_api_method_falls_back_to_web_search_when_no_provider(monkeypatch):
    sub_question = _sub_question(ResearchMethod.API)

    async def fake_api_lookup(sq):
        return None  # no provider registered

    async def fake_web_search(query, max_uses=4):
        return [{"url": "https://example.gov/data", "title": "Gov data", "snippet": "official figure"}]

    monkeypatch.setattr(researcher_module, "api_lookup", fake_api_lookup)
    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _FakeLLMClient())

    result = await researcher_module.researcher_node({"active_sub_question": sub_question})

    assert len(result["source_docs"]) == 1
    assert result["source_docs"][0].source_type == SourceType.GOV
    assert any("falling back to web search" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_both_method_merges_api_and_web_results(monkeypatch):
    sub_question = _sub_question(ResearchMethod.BOTH)

    async def fake_api_lookup(sq):
        return [{"url": "https://api.example.com/stat", "title": "Stat", "snippet": "42%"}]

    async def fake_web_search(query, max_uses=4):
        return [{"url": "https://news.example.com/story", "title": "Story", "snippet": "context"}]

    monkeypatch.setattr(researcher_module, "api_lookup", fake_api_lookup)
    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _FakeLLMClient())

    result = await researcher_module.researcher_node({"active_sub_question": sub_question})

    urls = {doc.url for doc in result["source_docs"]}
    assert urls == {"https://api.example.com/stat", "https://news.example.com/story"}


@pytest.mark.asyncio
async def test_total_search_failure_returns_empty_with_error(monkeypatch):
    sub_question = _sub_question(ResearchMethod.WEB_SEARCH)

    async def failing_web_search(query, max_uses=4):
        raise RuntimeError("network down")

    monkeypatch.setattr(researcher_module, "web_search", failing_web_search)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _FakeLLMClient())

    result = await researcher_module.researcher_node({"active_sub_question": sub_question})

    assert result["source_docs"] == []
    assert result["claims"] == []
    assert any("no sources found" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_claim_extraction_fallback_when_llm_not_configured(monkeypatch):
    sub_question = _sub_question(ResearchMethod.WEB_SEARCH)

    async def fake_web_search(query, max_uses=4):
        return [{"url": "https://example.com/a", "title": "A", "snippet": "X increased by 10% in 2026"}]

    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _FakeLLMClient(configured=False))

    result = await researcher_module.researcher_node({"active_sub_question": sub_question})

    assert len(result["claims"]) == 1
    assert result["claims"][0].confidence == 0.4  # fallback heuristic marker
    assert "10%" in result["claims"][0].claim_text


@pytest.mark.asyncio
async def test_researcher_node_dedupes_across_api_and_web_results(monkeypatch):
    """Same URL (cosmetically different) returned by both api_lookup and web_search should collapse to one doc."""
    sub_question = _sub_question(ResearchMethod.BOTH)

    async def fake_api_lookup(sq):
        return [{"url": "https://example.com/report?utm_source=x", "title": "Report", "snippet": "short"}]

    async def fake_web_search(query, max_uses=4):
        return [{"url": "https://www.example.com/report/", "title": "Report", "snippet": "a much longer excerpt with real detail"}]

    monkeypatch.setattr(researcher_module, "api_lookup", fake_api_lookup)
    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _FakeLLMClient())

    result = await researcher_module.researcher_node({"active_sub_question": sub_question})

    assert len(result["source_docs"]) == 1
    assert "much longer excerpt" in result["source_docs"][0].snippet


@pytest.mark.asyncio
async def test_researcher_node_flags_low_quality_sources(monkeypatch):
    sub_question = _sub_question(ResearchMethod.WEB_SEARCH)

    async def fake_web_search(query, max_uses=4):
        return [
            {"url": "https://quora.com/some-question", "title": "Q", "snippet": "a community answer about X"},
            {"url": "https://reuters.com/article", "title": "R", "snippet": "an official report about X", "page_age": "May 1, 2026"},
        ]

    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _FakeLLMClient())

    result = await researcher_module.researcher_node({"active_sub_question": sub_question})

    by_url = {doc.url: doc for doc in result["source_docs"]}
    quora_doc = by_url["https://quora.com/some-question"]
    reuters_doc = by_url["https://reuters.com/article"]

    assert "content_farm_domain" in quora_doc.quality_flags
    assert "no_date" in quora_doc.quality_flags
    assert "no_date" not in reuters_doc.quality_flags
    assert quora_doc.credibility_score < reuters_doc.credibility_score


@pytest.mark.asyncio
async def test_claim_extraction_failure_falls_back_gracefully(monkeypatch):
    sub_question = _sub_question(ResearchMethod.WEB_SEARCH)

    async def fake_web_search(query, max_uses=4):
        return [{"url": "https://example.com/a", "title": "A", "snippet": "some fact"}]

    monkeypatch.setattr(researcher_module, "web_search", fake_web_search)
    monkeypatch.setattr(researcher_module, "build_llm_client", lambda: _FakeLLMClient(should_raise=True))

    result = await researcher_module.researcher_node({"active_sub_question": sub_question})

    assert len(result["claims"]) == 1  # fallback still produced something
    assert any("claim extraction failed" in e for e in result["errors"])
