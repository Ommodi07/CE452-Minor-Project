"""
Critic node.

Unlike the Researcher (which extracts claims from one sub-question's own
sources, in isolation), the Critic sees every SourceDoc gathered across
every sub-question in this run at once — that's what makes genuine
cross-source corroboration/contradiction detection possible.

Two-step design, deliberately split between model and code:
  1. The model (LLMClient.extract_and_verify_claims) extracts claims and
     reports EVIDENCE ONLY — which sources support a claim, which
     contradict it. It does not decide corroborated/disputed/unverified.
  2. `_classify_claim` here computes that verdict deterministically: 2+
     independent sources (distinct domains) with no contradiction ->
     CORROBORATED; any contradiction -> DISPUTED; otherwise UNVERIFIED.

Keeping the classification in code (not trusted as a raw model judgment)
means the "2+ independent sources" rule is actually enforced and testable,
rather than whatever the model felt like calling it.

REFLECTION LOOP: a sub-question whose claims are too heavily
Unverified/Disputed (see UNVERIFIED_DISPUTED_RATIO_THRESHOLD) — or which
got no claims at all — is flagged for a follow-up Researcher pass. Rather
than just re-running the identical search, this node generates a REFINED
search query for each flagged sub-question (LLMClient.refine_search_query,
with a deterministic fallback) and writes it onto that SubQuestion's
`refined_query` field. The conditional edge in routing.py
(`route_after_critic`) re-dispatches Researcher via Send for exactly these
flagged sub-questions; Researcher then uses `refined_query` in place of
`question_text` as the actual search string. No changes to routing.py were
needed for this — it already re-dispatches whatever SubQuestion object is
currently in `state["sub_questions"]`, so populating `refined_query` here
is enough to change what the next pass searches for.

IMPORTANT state-design note: this node deduplicates SourceDocs across
branches for its OWN analysis (dedupe_source_docs), but does NOT return a
"source_docs" key. `source_docs` uses an `operator.add` reducer (needed for
the Researcher fan-out), which only ever APPENDS — returning a deduped
subset here would get concatenated onto the existing list, not replace it,
silently doubling entries. If you need a canonical deduped view of sources,
compute it downstream (as this node and the Writer both do locally) rather
than trying to write it back to the channel.
"""
from __future__ import annotations

import asyncio
import logging
from statistics import mean
from urllib.parse import urlparse

from app.graph.prompts.critic import CRITIC_SYSTEM_PROMPT, build_critic_prompt
from app.graph.prompts.reflection import REFLECTION_SYSTEM_PROMPT, build_reflection_prompt
from app.graph.state import GraphState
from app.models.schemas import SourceDoc, SubQuestion, VerificationStatus, VerifiedClaim
from app.services.llm_client import LLMClient, build_llm_client
from app.tools.dedup import dedupe_source_docs

logger = logging.getLogger(__name__)

_BASE_CONFIDENCE_BY_STATUS = {
    VerificationStatus.CORROBORATED: 0.85,
    VerificationStatus.DISPUTED: 0.35,
    VerificationStatus.UNVERIFIED: 0.55,
}
_DEFAULT_CREDIBILITY = 0.7  # used when a doc has no credibility_score set
_MIN_CONFIDENCE = 0.05
_MAX_CONFIDENCE = 0.99

# Reflection loop threshold: if this fraction (or more) of a sub-question's
# claims are Unverified or Disputed, trigger a refined follow-up search
# rather than accepting thin/contested coverage. Tune per how conservative
# you want the pipeline to be — lower catches more marginal cases at the
# cost of more re-research passes.
UNVERIFIED_DISPUTED_RATIO_THRESHOLD = 0.5


def _domain_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _classify_claim(
    supporting_urls: list[str], contradicting_urls: list[str], docs_by_url: dict[str, SourceDoc]
) -> tuple[VerificationStatus, float]:
    """
    Deterministic verdict from evidence the model reported. Independence is
    judged by distinct domains, not raw source count — two sources on the
    same domain (or re-running the same wire copy) aren't independent
    corroboration of each other.
    """
    independent_domains = {_domain_of(u) for u in supporting_urls}

    if contradicting_urls:
        status = VerificationStatus.DISPUTED
    elif len(independent_domains) >= 2:
        status = VerificationStatus.CORROBORATED
    else:
        status = VerificationStatus.UNVERIFIED

    credibility_scores = [
        docs_by_url[u].credibility_score
        for u in supporting_urls
        if docs_by_url[u].credibility_score is not None
    ]
    avg_credibility = mean(credibility_scores) if credibility_scores else _DEFAULT_CREDIBILITY

    confidence = _BASE_CONFIDENCE_BY_STATUS[status] * avg_credibility
    confidence = round(max(_MIN_CONFIDENCE, min(_MAX_CONFIDENCE, confidence)), 2)
    return status, confidence


def _build_verified_claim(evidence: dict, docs_by_url: dict[str, SourceDoc]) -> VerifiedClaim | None:
    primary_doc = docs_by_url.get(evidence["primary_source_url"])
    if primary_doc is None:
        return None  # already logged in LLMClient; defensive no-op here

    supporting_urls = list(dict.fromkeys([evidence["primary_source_url"], *evidence["supporting_source_urls"]]))
    contradicting_urls = evidence["contradicting_source_urls"]

    status, confidence = _classify_claim(supporting_urls, contradicting_urls, docs_by_url)

    return VerifiedClaim(
        source_doc_id=primary_doc.id,
        sub_question_id=primary_doc.sub_question_id,
        claim_text=evidence["claim_text"],
        confidence=confidence,
        supporting_excerpt=primary_doc.snippet,
        verification_status=status,
        corroborating_source_ids=[
            docs_by_url[u].id for u in supporting_urls if u != evidence["primary_source_url"]
        ],
        contradicting_source_ids=[docs_by_url[u].id for u in contradicting_urls],
        critic_notes=evidence.get("critic_notes", ""),
        adjusted_confidence=confidence,
    )


def _fallback_verified_claims(state: GraphState) -> list[VerifiedClaim]:
    """
    No LLM available: carry over the Researcher's per-sub-question draft
    claims as-is, marked UNVERIFIED (single-source by construction — genuine
    cross-source verification isn't possible without the model). Resolved
    against the RAW (non-deduped) source_docs, since dedup here is a local
    working copy for the LLM path, not something applied to draft claims.
    """
    raw_docs_by_id = {doc.id: doc for doc in state.get("source_docs", [])}
    verified: list[VerifiedClaim] = []
    for claim in state.get("claims", []):
        doc = raw_docs_by_id.get(claim.source_doc_id)
        if doc is None:
            continue
        verified.append(
            VerifiedClaim(
                source_doc_id=claim.source_doc_id,
                sub_question_id=claim.sub_question_id,
                claim_text=claim.claim_text,
                confidence=claim.confidence,
                supporting_excerpt=claim.supporting_excerpt,
                verification_status=VerificationStatus.UNVERIFIED,
                corroborating_source_ids=[],
                contradicting_source_ids=[],
                critic_notes="No LLM available for cross-source verification; carried over as single-source.",
                adjusted_confidence=claim.confidence,
            )
        )
    return verified


def _fallback_refined_query(sub_question: SubQuestion, problematic_claims: list[VerifiedClaim]) -> str:
    """Deterministic query refinement used when no LLM is available or the call fails."""
    if any(c.verification_status == VerificationStatus.DISPUTED for c in problematic_claims):
        return f"{sub_question.question_text} (reconcile conflicting reports; prefer official or primary sources)"
    return f"{sub_question.question_text} (find additional independent, authoritative sources)"


async def _refine_query_for(
    sub_question: SubQuestion, problematic_claims: list[VerifiedClaim], llm_client: LLMClient
) -> str:
    if llm_client.is_configured:
        try:
            return await llm_client.refine_search_query(
                sub_question=sub_question,
                problematic_claims=problematic_claims,
                system_prompt=REFLECTION_SYSTEM_PROMPT,
                user_prompt=build_reflection_prompt(sub_question, problematic_claims),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "refine_search_query failed for sub_question=%s, using fallback: %s", sub_question.id, exc
            )
    return _fallback_refined_query(sub_question, problematic_claims)


def _assess_sub_questions(
    sub_questions: list[SubQuestion], verified_claims: list[VerifiedClaim]
) -> tuple[list[str], list[str], list[tuple[int, SubQuestion, list[VerifiedClaim]]]]:
    """
    For each sub-question, decide whether it needs a reflection pass:
      - zero claims at all (coverage gap), or
      - claims exist, but >= UNVERIFIED_DISPUTED_RATIO_THRESHOLD of them are
        Unverified/Disputed (quality gap).

    Returns (critic_feedback, open_questions, reflection_targets), where
    reflection_targets is [(index_into_sub_questions, sub_question,
    problematic_claims)] — problematic_claims is [] for the coverage-gap
    case (nothing to show the refinement step) and non-empty for the
    quality-gap case.
    """
    claims_by_sub_question: dict[str, list[VerifiedClaim]] = {}
    for vc in verified_claims:
        claims_by_sub_question.setdefault(vc.sub_question_id, []).append(vc)

    critic_feedback: list[str] = []
    open_questions: list[str] = []
    reflection_targets: list[tuple[int, SubQuestion, list[VerifiedClaim]]] = []

    for idx, sq in enumerate(sub_questions):
        sq_claims = claims_by_sub_question.get(sq.id, [])

        if not sq_claims:
            critic_feedback.append(f"No verified claims for sub-question: {sq.question_text}")
            open_questions.append(sq.question_text)
            reflection_targets.append((idx, sq, []))
            continue

        problematic = [c for c in sq_claims if c.verification_status != VerificationStatus.CORROBORATED]
        ratio = len(problematic) / len(sq_claims)
        if ratio >= UNVERIFIED_DISPUTED_RATIO_THRESHOLD:
            critic_feedback.append(
                f"{len(problematic)}/{len(sq_claims)} claims Unverified/Disputed "
                f"(>= {UNVERIFIED_DISPUTED_RATIO_THRESHOLD:.0%} threshold) for sub-question: "
                f"{sq.question_text} — refining search query"
            )
            open_questions.append(sq.question_text)
            reflection_targets.append((idx, sq, problematic))

    return critic_feedback, open_questions, reflection_targets


async def critic_node(state: GraphState) -> dict:
    errors: list[str] = []
    raw_source_docs = state.get("source_docs", [])

    # Local-only cross-branch dedup for this node's own analysis (see module
    # docstring for why this is never written back to state["source_docs"]).
    deduped_docs = dedupe_source_docs(raw_source_docs)
    if len(deduped_docs) < len(raw_source_docs):
        logger.info(
            "critic: deduped %d cross-branch duplicate source(s) (%d -> %d)",
            len(raw_source_docs) - len(deduped_docs),
            len(raw_source_docs),
            len(deduped_docs),
        )

    verified_claims: list[VerifiedClaim] = []

    if deduped_docs:
        llm_client = build_llm_client()
        if llm_client.is_configured:
            try:
                evidence_list = await llm_client.extract_and_verify_claims(
                    source_docs=deduped_docs,
                    system_prompt=CRITIC_SYSTEM_PROMPT,
                    user_prompt=build_critic_prompt(deduped_docs),
                )
                docs_by_url = {doc.url: doc for doc in deduped_docs}
                verified_claims = [
                    vc
                    for vc in (_build_verified_claim(ev, docs_by_url) for ev in evidence_list)
                    if vc is not None
                ]
            except Exception as exc:  # noqa: BLE001
                logger.warning("Critic LLM call failed, using fallback verification: %s", exc)
                errors.append(f"critic: LLM call failed, used fallback verification ({exc})")
                verified_claims = _fallback_verified_claims(state)
        else:
            verified_claims = _fallback_verified_claims(state)

    sub_questions = state.get("sub_questions", [])
    critic_feedback, open_questions, reflection_targets = _assess_sub_questions(sub_questions, verified_claims)

    # Only bother generating refined queries if there's actually going to be
    # another pass — skip the (LLM-call) cost if we're about to hit the
    # iteration cap and go straight to the writer regardless.
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 2)
    will_loop_again = bool(reflection_targets) and (iteration_count + 1) < max_iterations

    updated_sub_questions = list(sub_questions)
    if will_loop_again:
        llm_client = build_llm_client()
        refined = await asyncio.gather(
            *(
                _refine_query_for(sq, problematic_claims, llm_client)
                for _, sq, problematic_claims in reflection_targets
            )
        )
        for (idx, sq, _), refined_query in zip(reflection_targets, refined):
            updated_sub_questions[idx] = sq.model_copy(update={"refined_query": refined_query})

    result: dict = {
        "sub_questions": updated_sub_questions,
        "verified_claims": verified_claims,
        "critic_feedback": critic_feedback,
        "open_questions": open_questions,
        "iteration_count": iteration_count + 1,
        "status": "critiquing",
    }
    if errors:
        result["errors"] = errors
    return result
