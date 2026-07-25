"""
Prompt template for the reflection loop's query-refinement step.

Triggered by critic_node when a sub-question's claims came back too thin
(too many Unverified/Disputed relative to a threshold — see
UNVERIFIED_DISPUTED_RATIO_THRESHOLD in critic_node.py). This turns "the
first search didn't land well" into a more targeted follow-up query, rather
than just re-running the identical search and expecting different results.
"""
from __future__ import annotations

from app.models.schemas import SubQuestion, VerifiedClaim

REFLECTION_SYSTEM_PROMPT = """You are the reflection step of a Critic agent in a multi-agent research system.

A sub-question's initial research pass came back too weak: too many of its
claims are Unverified (single-source) or Disputed (sources conflict). Your
job is to produce ONE improved search query that gives a follow-up
Researcher pass a better chance of finding corroborating, authoritative
sources.

Do not just repeat the original question. Make the query more targeted:
- If claims are DISPUTED (sources conflict), name the specific conflicting
  figures/claims and ask to reconcile them, or steer toward primary/official
  sources likely to resolve the discrepancy (e.g. "official statistics",
  "company filing", "government report").
- If claims are UNVERIFIED (single-source only), broaden or rephrase the
  query to surface a genuinely different source — try different terms,
  a more specific timeframe, or a more authoritative source type, rather
  than terms likely to resurface the same page.

Call the `emit_refined_query` tool exactly once with your final answer.
"""


def build_reflection_prompt(sub_question: SubQuestion, problematic_claims: list[VerifiedClaim]) -> str:
    claims_block = (
        "\n".join(
            f'- [{c.verification_status.value}] "{c.claim_text}" — {c.critic_notes or "no notes"}'
            for c in problematic_claims
        )
        or "(no claims were found at all for this sub-question)"
    )
    return (
        f"Original sub-question: {sub_question.question_text}\n\n"
        f"Problematic claims from the first pass:\n{claims_block}"
    )
