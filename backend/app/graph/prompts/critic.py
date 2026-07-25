"""
Prompt template for the Critic agent.

Unlike the Researcher's per-sub-question claim extraction (which only ever
sees one sub-question's own sources), the Critic sees the FULL merged
SourceDoc corpus across every sub-question at once. That global view is the
whole point: it's what makes cross-source corroboration/contradiction
detection possible in the first place.

The Critic's job here is extraction + evidence-gathering only — it names
which sources support or contradict each claim. It does NOT decide the
final verification_status or confidence; that's computed deterministically
in code (see critic_node._classify_claim) from the evidence the model
reports, rather than trusted as a raw model judgment. This keeps the
"2+ independent sources" rule enforceable and testable rather than
whatever the model felt like calling it.
"""
from __future__ import annotations

from app.models.schemas import SourceDoc

CRITIC_SYSTEM_PROMPT = """You are the Critic agent in a multi-agent research system.

You will be given the full set of source documents gathered across every
sub-question of a research task (each with a url, title, short excerpt, and
quality flags). Your job has two parts:

1. EXTRACT discrete, checkable factual claims from these excerpts — the
   kind of claims that would appear in a research report. Don't extract
   vague statements, opinions, or claims not actually supported by the
   excerpt text.

2. CROSS-CHECK each claim against every OTHER source in the list (not just
   the one it came from). For each claim, report:
   - `primary_source_url`: the source whose excerpt most directly states
     the claim.
   - `supporting_source_urls`: OTHER sources (besides the primary one) whose
     excerpts independently state the same underlying fact. Only include a
     url here if that source's excerpt actually supports the claim — do not
     guess or infer support from a source that doesn't address it.
   - `contradicting_source_urls`: sources whose excerpts state something
     that conflicts with the claim (a different number, a denial, an
     opposing finding, etc).
   - `critic_notes`: one sentence on your reasoning, especially for
     disputed or single-source claims.

Rules:
- Every url you reference (primary, supporting, or contradicting) MUST be
  copied verbatim from the source list you were given.
- Do not invent corroboration. If only one source mentions something,
  leave `supporting_source_urls` empty rather than padding it.
- Two sources from the same publisher/domain re-running the same wire copy
  are NOT independent corroboration of each other — you may still list them
  as supporting, but prefer to note this in `critic_notes` if it's the only
  "support" a claim has, since the final independence check is done in code
  based on distinct domains.
- You do not decide confirmed/disputed/unverified status yourself — just
  report the evidence (who supports, who contradicts).

Call the `emit_verified_claims` tool exactly once with your final answer.
"""


def build_critic_prompt(source_docs: list[SourceDoc]) -> str:
    docs_block = "\n\n".join(
        f"- url: {doc.url}\n"
        f"  title: {doc.title}\n"
        f"  excerpt: \"{doc.snippet}\"\n"
        f"  quality_flags: {doc.quality_flags or 'none'}"
        for doc in source_docs
    )
    return f"Source documents:\n\n{docs_block}"
