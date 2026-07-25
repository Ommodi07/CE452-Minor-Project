import pytest

from app.graph.nodes import writer as writer_module
from app.models.schemas import (
    ResearchAngle,
    ResearchMethod,
    SourceDoc,
    SubQuestion,
    VerificationStatus,
    VerifiedClaim,
)


def _doc(url, title="T") -> SourceDoc:
    return SourceDoc(sub_question_id="sq", url=url, title=title, snippet="s")


def _sub_question(text="q") -> SubQuestion:
    return SubQuestion(
        parent_query="test", question_text=text,
        angle=ResearchAngle.FACTUAL, research_method=ResearchMethod.WEB_SEARCH,
    )


class _FakeLLMClient:
    def __init__(self, summary="An LLM-written summary.", should_raise=False, configured=True):
        self._summary = summary
        self._should_raise = should_raise
        self._configured = configured

    @property
    def is_configured(self):
        return self._configured

    async def complete(self, system_prompt, user_prompt):
        if self._should_raise:
            raise RuntimeError("simulated writer failure")
        return self._summary


# ---- Citation registry ----

def test_citation_registry_assigns_sequential_numbers_on_first_use():
    doc_a, doc_b = _doc("https://a.com"), _doc("https://b.com")
    registry = writer_module._CitationRegistry({doc_a.id: doc_a, doc_b.id: doc_b})

    assert registry.cite(doc_a.id) == "[1]"
    assert registry.cite(doc_b.id) == "[2]"
    assert registry.cite(doc_a.id) == "[1]"  # reused, not re-numbered


def test_citation_registry_references_markdown_lists_in_number_order():
    doc_a, doc_b = _doc("https://a.com", "A"), _doc("https://b.com", "B")
    registry = writer_module._CitationRegistry({doc_a.id: doc_a, doc_b.id: doc_b})
    registry.cite(doc_b.id)  # b cited first -> gets [1]
    registry.cite(doc_a.id)  # a cited second -> gets [2]

    refs = registry.references_markdown()
    lines = refs.splitlines()
    assert lines[0].startswith("1. [B]")
    assert lines[1].startswith("2. [A]")


def test_citation_registry_includes_quality_flags_in_references():
    doc = _doc("https://quora.com/x", "Q")
    doc.quality_flags = ["content_farm_domain", "no_date"]
    registry = writer_module._CitationRegistry({doc.id: doc})
    registry.cite(doc.id)

    assert "content_farm_domain" in registry.references_markdown()


# ---- Claim line rendering (the "disputed claims never silently dropped" requirement) ----

def test_disputed_claim_is_explicitly_labeled_and_cites_both_sides():
    doc_a, doc_b = _doc("https://a.com"), _doc("https://b.com")
    registry = writer_module._CitationRegistry({doc_a.id: doc_a, doc_b.id: doc_b})
    claim = VerifiedClaim(
        source_doc_id=doc_a.id, sub_question_id="sq", claim_text="Rates rose 0.5%",
        confidence=0.4, supporting_excerpt="", verification_status=VerificationStatus.DISPUTED,
        corroborating_source_ids=[], contradicting_source_ids=[doc_b.id],
        critic_notes="Source B reports a different figure.", adjusted_confidence=0.4,
    )
    line = writer_module._render_claim_line(claim, registry)

    assert "**Disputed:**" in line
    assert "Rates rose 0.5%" in line
    assert "[1]" in line  # supporting
    assert "[2]" in line  # contradicting
    assert "Source B reports a different figure." in line


def test_unverified_claim_is_labeled_single_source():
    doc = _doc("https://a.com")
    registry = writer_module._CitationRegistry({doc.id: doc})
    claim = VerifiedClaim(
        source_doc_id=doc.id, sub_question_id="sq", claim_text="X happened",
        confidence=0.5, supporting_excerpt="", verification_status=VerificationStatus.UNVERIFIED,
        corroborating_source_ids=[], contradicting_source_ids=[], critic_notes="",
        adjusted_confidence=0.5,
    )
    line = writer_module._render_claim_line(claim, registry)

    assert "unverified" in line.lower()
    assert "[1]" in line


def test_corroborated_claim_cites_all_supporting_sources_without_disputed_label():
    doc_a, doc_b = _doc("https://a.com"), _doc("https://b.com")
    registry = writer_module._CitationRegistry({doc_a.id: doc_a, doc_b.id: doc_b})
    claim = VerifiedClaim(
        source_doc_id=doc_a.id, sub_question_id="sq", claim_text="Widely reported fact",
        confidence=0.9, supporting_excerpt="", verification_status=VerificationStatus.CORROBORATED,
        corroborating_source_ids=[doc_b.id], contradicting_source_ids=[], critic_notes="",
        adjusted_confidence=0.9,
    )
    line = writer_module._render_claim_line(claim, registry)

    assert "Disputed" not in line
    assert "[1]" in line and "[2]" in line


# ---- writer_node integration ----

@pytest.mark.asyncio
async def test_writer_node_never_drops_disputed_claims(monkeypatch):
    sub_question = _sub_question("is X true?")
    doc_a, doc_b = _doc("https://a.com"), _doc("https://b.com")
    disputed_claim = VerifiedClaim(
        source_doc_id=doc_a.id, sub_question_id=sub_question.id, claim_text="Disputed fact about X",
        confidence=0.3, supporting_excerpt="", verification_status=VerificationStatus.DISPUTED,
        corroborating_source_ids=[], contradicting_source_ids=[doc_b.id],
        critic_notes="conflicting reports", adjusted_confidence=0.3,
    )
    monkeypatch.setattr(writer_module, "build_llm_client", lambda: _FakeLLMClient())

    state = {
        "session_id": "s1", "original_query": "is X true?",
        "sub_questions": [sub_question], "verified_claims": [disputed_claim],
        "source_docs": [doc_a, doc_b], "open_questions": [],
    }
    result = await writer_module.writer_node(state)

    report = result["report"]
    assert "Disputed fact about X" in report.markdown
    assert "**Disputed:**" in report.markdown
    assert result["status"] == "done"


@pytest.mark.asyncio
async def test_writer_node_notes_sub_questions_with_no_findings():
    sq_covered = _sub_question("covered question")
    sq_gap = _sub_question("uncovered question")
    doc = _doc("https://a.com")
    claim = VerifiedClaim(
        source_doc_id=doc.id, sub_question_id=sq_covered.id, claim_text="Some fact",
        confidence=0.8, supporting_excerpt="", verification_status=VerificationStatus.UNVERIFIED,
        corroborating_source_ids=[], contradicting_source_ids=[], critic_notes="",
        adjusted_confidence=0.8,
    )

    state = {
        "session_id": "s1", "original_query": "test query",
        "sub_questions": [sq_covered, sq_gap], "verified_claims": [claim],
        "source_docs": [doc], "open_questions": [sq_gap.question_text],
    }
    result = await writer_module.writer_node(state)

    report = result["report"]
    assert "No verified claims were found" in report.markdown
    assert sq_gap.question_text in report.limitations


@pytest.mark.asyncio
async def test_writer_node_uses_llm_executive_summary_when_configured(monkeypatch):
    sub_question = _sub_question()
    monkeypatch.setattr(writer_module, "build_llm_client", lambda: _FakeLLMClient(summary="Custom summary."))

    state = {
        "session_id": "s1", "original_query": "q", "sub_questions": [sub_question],
        "verified_claims": [], "source_docs": [], "open_questions": [],
    }
    result = await writer_module.writer_node(state)

    assert result["report"].executive_summary == "Custom summary."


@pytest.mark.asyncio
async def test_writer_node_falls_back_to_deterministic_summary_on_llm_failure(monkeypatch):
    sub_question = _sub_question()
    monkeypatch.setattr(writer_module, "build_llm_client", lambda: _FakeLLMClient(should_raise=True))

    state = {
        "session_id": "s1", "original_query": "q", "sub_questions": [sub_question],
        "verified_claims": [], "source_docs": [], "open_questions": [],
    }
    result = await writer_module.writer_node(state)

    assert "claim(s)" in result["report"].executive_summary
    assert any("executive summary" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_writer_node_falls_back_when_llm_not_configured():
    sub_question = _sub_question()
    state = {
        "session_id": "s1", "original_query": "q", "sub_questions": [sub_question],
        "verified_claims": [], "source_docs": [], "open_questions": [],
    }
    result = await writer_module.writer_node(state)

    assert "0 corroborated" in result["report"].executive_summary


@pytest.mark.asyncio
async def test_writer_node_markdown_includes_title_sections_and_references(monkeypatch):
    sub_question = _sub_question("what is X?")
    doc = _doc("https://reuters.com/x", "Reuters article")
    claim = VerifiedClaim(
        source_doc_id=doc.id, sub_question_id=sub_question.id, claim_text="X is true",
        confidence=0.6, supporting_excerpt="", verification_status=VerificationStatus.UNVERIFIED,
        corroborating_source_ids=[], contradicting_source_ids=[], critic_notes="",
        adjusted_confidence=0.6,
    )
    monkeypatch.setattr(writer_module, "build_llm_client", lambda: _FakeLLMClient())

    state = {
        "session_id": "s1", "original_query": "what is X?", "sub_questions": [sub_question],
        "verified_claims": [claim], "source_docs": [doc], "open_questions": [],
    }
    result = await writer_module.writer_node(state)
    md = result["report"].markdown

    assert md.startswith("# Research Report: what is X?")
    assert "## what is X?" in md
    assert "## References" in md
    assert "[Reuters article](https://reuters.com/x)" in md
