import pytest

from app.graph.nodes import critic as critic_module
from app.models.schemas import (
    Claim,
    ResearchAngle,
    ResearchMethod,
    SourceDoc,
    SourceType,
    SubQuestion,
    VerificationStatus,
)


def _doc(url, sub_question_id, snippet="content", source_type=SourceType.OTHER, credibility_score=0.8):
    return SourceDoc(
        sub_question_id=sub_question_id,
        url=url,
        title=url,
        snippet=snippet,
        source_type=source_type,
        credibility_score=credibility_score,
    )


def _sub_question(text="q") -> SubQuestion:
    return SubQuestion(
        parent_query="test", question_text=text,
        angle=ResearchAngle.FACTUAL, research_method=ResearchMethod.WEB_SEARCH,
    )


class _FakeLLMClient:
    def __init__(self, evidence=None, should_raise=False, configured=True):
        self._evidence = evidence or []
        self._should_raise = should_raise
        self._configured = configured

    @property
    def is_configured(self):
        return self._configured

    async def extract_and_verify_claims(self, *, source_docs, system_prompt, user_prompt):
        if self._should_raise:
            raise RuntimeError("simulated critic failure")
        return self._evidence


# ---- _classify_claim unit tests (pure function, no mocking needed) ----

def test_classify_corroborated_when_two_independent_domains_agree():
    doc_a = _doc("https://a.com/1", "sq1")
    doc_b = _doc("https://b.com/1", "sq1")
    docs_by_url = {doc_a.url: doc_a, doc_b.url: doc_b}

    status, _ = critic_module._classify_claim([doc_a.url, doc_b.url], [], docs_by_url)
    assert status == VerificationStatus.CORROBORATED


def test_classify_unverified_when_single_source():
    doc_a = _doc("https://a.com/1", "sq1")
    docs_by_url = {doc_a.url: doc_a}

    status, _ = critic_module._classify_claim([doc_a.url], [], docs_by_url)
    assert status == VerificationStatus.UNVERIFIED


def test_classify_unverified_when_same_domain_twice_not_independent():
    doc_a = _doc("https://a.com/1", "sq1")
    doc_a2 = _doc("https://a.com/2", "sq1")
    docs_by_url = {doc_a.url: doc_a, doc_a2.url: doc_a2}

    # Two pages on the SAME domain shouldn't count as 2 independent sources.
    status, _ = critic_module._classify_claim([doc_a.url, doc_a2.url], [], docs_by_url)
    assert status == VerificationStatus.UNVERIFIED


def test_classify_disputed_when_any_contradiction_present_even_with_corroboration():
    doc_a = _doc("https://a.com/1", "sq1")
    doc_b = _doc("https://b.com/1", "sq1")
    doc_c = _doc("https://c.com/1", "sq1")
    docs_by_url = {d.url: d for d in (doc_a, doc_b, doc_c)}

    status, _ = critic_module._classify_claim([doc_a.url, doc_b.url], [doc_c.url], docs_by_url)
    assert status == VerificationStatus.DISPUTED


def test_classify_confidence_scales_with_source_credibility():
    high_cred = _doc("https://a.com/1", "sq1", credibility_score=0.9)
    high_cred2 = _doc("https://b.com/1", "sq1", credibility_score=0.9)
    low_cred = _doc("https://c.com/1", "sq1", credibility_score=0.2)
    low_cred2 = _doc("https://d.com/1", "sq1", credibility_score=0.2)

    _, high_confidence = critic_module._classify_claim(
        [high_cred.url, high_cred2.url], [], {high_cred.url: high_cred, high_cred2.url: high_cred2}
    )
    _, low_confidence = critic_module._classify_claim(
        [low_cred.url, low_cred2.url], [], {low_cred.url: low_cred, low_cred2.url: low_cred2}
    )
    assert high_confidence > low_confidence


# ---- critic_node integration tests (mocked LLM client) ----

@pytest.mark.asyncio
async def test_critic_node_corroborates_claim_from_two_independent_sources(monkeypatch):
    sub_question = _sub_question()
    doc_a = _doc("https://reuters.com/story", sub_question.id, snippet="Rates rose 0.5%")
    doc_b = _doc("https://apnews.com/story", sub_question.id, snippet="Rates increased by half a point")

    evidence = [
        {
            "claim_text": "Interest rates rose by 0.5%",
            "primary_source_url": doc_a.url,
            "supporting_source_urls": [doc_b.url],
            "contradicting_source_urls": [],
            "critic_notes": "Both outlets report the same figure.",
        }
    ]
    monkeypatch.setattr(critic_module, "build_llm_client", lambda: _FakeLLMClient(evidence))

    state = {"source_docs": [doc_a, doc_b], "sub_questions": [sub_question], "claims": []}
    result = await critic_module.critic_node(state)

    assert len(result["verified_claims"]) == 1
    vc = result["verified_claims"][0]
    assert vc.verification_status == VerificationStatus.CORROBORATED
    assert doc_b.id in vc.corroborating_source_ids
    assert result["open_questions"] == []


@pytest.mark.asyncio
async def test_critic_node_flags_gap_for_sub_question_with_no_claims(monkeypatch):
    sq1 = _sub_question("question with coverage")
    sq2 = _sub_question("question with no coverage")
    doc_a = _doc("https://reuters.com/1", sq1.id)
    doc_b = _doc("https://apnews.com/1", sq1.id)

    evidence = [
        {
            "claim_text": "Some well-corroborated claim",
            "primary_source_url": doc_a.url,
            "supporting_source_urls": [doc_b.url],  # 2 independent domains -> CORROBORATED, not a reflection target
            "contradicting_source_urls": [],
            "critic_notes": "two independent outlets agree",
        }
    ]
    monkeypatch.setattr(critic_module, "build_llm_client", lambda: _FakeLLMClient(evidence))

    state = {"source_docs": [doc_a, doc_b], "sub_questions": [sq1, sq2], "claims": []}
    result = await critic_module.critic_node(state)

    assert sq2.question_text in result["open_questions"]
    assert sq1.question_text not in result["open_questions"]


@pytest.mark.asyncio
async def test_critic_node_falls_back_to_draft_claims_when_not_configured(monkeypatch):
    doc_a = _doc("https://example.com/1", "sq1")
    sub_question = _sub_question()
    draft_claim = Claim(
        source_doc_id=doc_a.id, sub_question_id=sub_question.id,
        claim_text="Draft claim from researcher", confidence=0.6, supporting_excerpt="content",
    )

    class _Unconfigured:
        is_configured = False

    monkeypatch.setattr(critic_module, "build_llm_client", lambda: _Unconfigured())

    state = {"source_docs": [doc_a], "sub_questions": [sub_question], "claims": [draft_claim]}
    result = await critic_module.critic_node(state)

    assert len(result["verified_claims"]) == 1
    vc = result["verified_claims"][0]
    assert vc.verification_status == VerificationStatus.UNVERIFIED
    assert vc.claim_text == "Draft claim from researcher"


@pytest.mark.asyncio
async def test_critic_node_falls_back_on_llm_exception(monkeypatch):
    doc_a = _doc("https://example.com/1", "sq1")
    sub_question = _sub_question()
    draft_claim = Claim(
        source_doc_id=doc_a.id, sub_question_id=sub_question.id,
        claim_text="Draft claim", confidence=0.5, supporting_excerpt="content",
    )
    monkeypatch.setattr(critic_module, "build_llm_client", lambda: _FakeLLMClient(should_raise=True))

    state = {"source_docs": [doc_a], "sub_questions": [sub_question], "claims": [draft_claim]}
    result = await critic_module.critic_node(state)

    assert len(result["verified_claims"]) == 1
    assert any("critic: LLM call failed" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_critic_node_dedupes_cross_branch_duplicates_before_analysis(monkeypatch):
    """
    Same URL appearing under two different sub-questions' source_docs (the
    scenario Researcher-level dedup can't catch, since it never sees other
    branches' results) should collapse to one doc before evidence-gathering.
    """
    doc_from_sq1 = _doc("https://example.com/shared?utm_source=x", "sq1", snippet="short")
    doc_from_sq2 = _doc("https://www.example.com/shared/", "sq2", snippet="a much richer, longer excerpt")

    captured_docs = {}

    class _CapturingLLMClient:
        is_configured = True

        async def extract_and_verify_claims(self, *, source_docs, system_prompt, user_prompt):
            captured_docs["docs"] = source_docs
            return []

    monkeypatch.setattr(critic_module, "build_llm_client", lambda: _CapturingLLMClient())

    state = {
        "source_docs": [doc_from_sq1, doc_from_sq2],
        "sub_questions": [_sub_question("a"), _sub_question("b")],
        "claims": [],
    }
    await critic_module.critic_node(state)

    assert len(captured_docs["docs"]) == 1


@pytest.mark.asyncio
async def test_critic_node_handles_empty_source_docs():
    sub_question = _sub_question()
    state = {"source_docs": [], "sub_questions": [sub_question], "claims": []}
    result = await critic_module.critic_node(state)

    assert result["verified_claims"] == []
    assert sub_question.question_text in result["open_questions"]
