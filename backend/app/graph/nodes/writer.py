"""
Writer node. Terminal node in the graph.

Deliberately split between code and model, same philosophy as the Critic:
  - Section bodies, citation numbering, and Corroborated/Disputed/Unverified
    callouts are assembled DETERMINISTICALLY in code from VerifiedClaim data.
    Every claim that exists gets rendered — a Disputed claim is never
    dropped, it's rendered with an explicit "**Disputed:**" callout and both
    its supporting and contradicting sources cited. This is a correctness
    requirement, not a style choice, so it isn't left to model judgment.
  - Only the executive summary is LLM-authored (LLMClient.complete) — the
    one part of the report that's genuinely open-ended synthesis rather
    than data with a fixed rendering.

Citation numbering: a source gets its number the first time any claim
references it (as primary, corroborating, or contradicting), in the order
sections are rendered. The same source reused later reuses its existing
number — this is standard endnote-style numbering, not per-section.
"""
from __future__ import annotations

import logging

from app.graph.prompts.writer import WRITER_SYSTEM_PROMPT, build_writer_prompt
from app.graph.state import GraphState
from app.models.schemas import (
    Report,
    ReportSection,
    SourceDoc,
    SubQuestion,
    VerificationStatus,
    VerifiedClaim,
)
from app.services.llm_client import build_llm_client

logger = logging.getLogger(__name__)

_STATUS_LABEL = {
    VerificationStatus.CORROBORATED: "Corroborated",
    VerificationStatus.DISPUTED: "Disputed",
    VerificationStatus.UNVERIFIED: "Unverified",
}


class _CitationRegistry:
    """Assigns and tracks stable [N] numbers for sources as they're first cited."""

    def __init__(self, docs_by_id: dict[str, SourceDoc]):
        self._docs_by_id = docs_by_id
        self._number_by_id: dict[str, int] = {}

    def cite(self, doc_id: str) -> str:
        """Return the '[N]' marker for doc_id, assigning a new number on first use."""
        number = self._number_by_id.get(doc_id)
        if number is None:
            number = len(self._number_by_id) + 1
            self._number_by_id[doc_id] = number
        return f"[{number}]"

    def cite_all(self, doc_ids: list[str]) -> str:
        return "".join(self.cite(doc_id) for doc_id in doc_ids if doc_id in self._docs_by_id)

    def references_markdown(self) -> str:
        if not self._number_by_id:
            return "_No sources were cited._"
        ordered = sorted(self._number_by_id.items(), key=lambda pair: pair[1])
        lines = []
        for doc_id, number in ordered:
            doc = self._docs_by_id.get(doc_id)
            if doc is None:
                continue
            flags = f" _({', '.join(doc.quality_flags)})_" if doc.quality_flags else ""
            lines.append(f"{number}. [{doc.title}]({doc.url}){flags}")
        return "\n".join(lines)

    def citations_dict(self) -> dict[str, SourceDoc]:
        return {doc_id: self._docs_by_id[doc_id] for doc_id in self._number_by_id if doc_id in self._docs_by_id}


def _render_claim_line(claim: VerifiedClaim, registry: _CitationRegistry) -> str:
    supporting_ids = [claim.source_doc_id, *claim.corroborating_source_ids]
    supporting_marks = registry.cite_all(supporting_ids)

    if claim.verification_status == VerificationStatus.DISPUTED:
        contradicting_marks = registry.cite_all(claim.contradicting_source_ids)
        note = f" {claim.critic_notes}" if claim.critic_notes else ""
        return (
            f"- **Disputed:** {claim.claim_text} {supporting_marks}, "
            f"contradicted by {contradicting_marks}.{note}"
        )

    if claim.verification_status == VerificationStatus.UNVERIFIED:
        return f"- {claim.claim_text} {supporting_marks} *(unverified — single source)*"

    # CORROBORATED
    return f"- {claim.claim_text} {supporting_marks}"


def _render_section(sub_question: SubQuestion, claims: list[VerifiedClaim], registry: _CitationRegistry) -> ReportSection:
    if not claims:
        content = "_No verified claims were found for this sub-question._"
    else:
        content = "\n".join(_render_claim_line(c, registry) for c in claims)

    return ReportSection(
        heading=sub_question.question_text,
        content=content,
        cited_claim_ids=[c.id for c in claims],
    )


def _fallback_executive_summary(
    verified_claims: list[VerifiedClaim], open_questions: list[str]
) -> str:
    counts = {status: 0 for status in VerificationStatus}
    for c in verified_claims:
        counts[c.verification_status] += 1
    total = len(verified_claims)

    summary = (
        f"This report is based on {total} claim(s): "
        f"{counts[VerificationStatus.CORROBORATED]} corroborated by multiple independent sources, "
        f"{counts[VerificationStatus.DISPUTED]} disputed by conflicting sources, and "
        f"{counts[VerificationStatus.UNVERIFIED]} unverified (single source only)."
    )
    if open_questions:
        summary += f" {len(open_questions)} sub-question(s) had no verified findings."
    return summary


def _assemble_markdown(report: Report, sections_markdown: list[str], references_markdown: str) -> str:
    parts = [f"# {report.title}", "", report.executive_summary, ""]
    for heading, content in zip((s.heading for s in report.sections), sections_markdown):
        parts.extend([f"## {heading}", "", content, ""])
    if report.limitations:
        parts.append("## Limitations")
        parts.append("")
        parts.extend(f"- {item}" for item in report.limitations)
        parts.append("")
    parts.append("## References")
    parts.append("")
    parts.append(references_markdown)
    return "\n".join(parts)


async def writer_node(state: GraphState) -> dict:
    original_query = state["original_query"]
    sub_questions = state.get("sub_questions", [])
    verified_claims = state.get("verified_claims", [])
    open_questions = state.get("open_questions", [])
    docs_by_id = {doc.id: doc for doc in state.get("source_docs", [])}

    registry = _CitationRegistry(docs_by_id)

    claims_by_sub_question: dict[str, list[VerifiedClaim]] = {}
    for c in verified_claims:
        claims_by_sub_question.setdefault(c.sub_question_id, []).append(c)

    sections: list[ReportSection] = []
    sections_markdown: list[str] = []
    for sq in sub_questions:
        section = _render_section(sq, claims_by_sub_question.get(sq.id, []), registry)
        sections.append(section)
        sections_markdown.append(section.content)

    errors: list[str] = []
    llm_client = build_llm_client()
    if llm_client.is_configured:
        try:
            executive_summary = await llm_client.complete(
                system_prompt=WRITER_SYSTEM_PROMPT,
                user_prompt=build_writer_prompt(original_query, sub_questions, verified_claims, open_questions),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Writer executive summary LLM call failed, using fallback: %s", exc)
            errors.append(f"writer: executive summary LLM call failed, used fallback ({exc})")
            executive_summary = _fallback_executive_summary(verified_claims, open_questions)
    else:
        executive_summary = _fallback_executive_summary(verified_claims, open_questions)

    report = Report(
        session_id=state["session_id"],
        title=f"Research Report: {original_query}",
        executive_summary=executive_summary,
        sections=sections,
        citations=registry.citations_dict(),
        limitations=open_questions,
    )
    report.markdown = _assemble_markdown(report, sections_markdown, registry.references_markdown())

    result: dict = {"report": report, "status": "done"}
    if errors:
        result["errors"] = errors
    return result
