"""
Prompt template for the Writer agent — specifically, just its executive
summary. Everything else in the report (section bodies, citation numbers,
Disputed/Unverified callouts, the References list) is assembled
deterministically in code, not by the model.

Why the split: citation correctness and "disputed claims must never be
silently dropped" are hard requirements. An LLM asked to write the whole
report from scratch could paraphrase a claim in a way that drops its
citation, or soften a Disputed claim into reading as settled fact. Neither
is acceptable here, so the model's job is narrowed to what prose genuinely
adds value for — a high-level synthesis — while every fact-bearing,
citation-bearing sentence in the body comes straight from code, from data.
"""
from __future__ import annotations

from app.models.schemas import SubQuestion, VerifiedClaim

WRITER_SYSTEM_PROMPT = """You are the Writer agent in a multi-agent research system.

Your ONLY job is to write a short executive summary (2-4 sentences) that
gives a reader the big-picture answer to the research query before they
read the full report.

Rules:
1. Base the summary ONLY on the claims and status counts you're given.
   Do not introduce any fact, figure, or claim that isn't in the input.
2. Do not include citation markers or source names — that's the report
   body's job, not the summary's.
3. If a significant portion of claims are Disputed or Unverified, say so
   plainly in the summary (e.g. "though some figures are disputed" /
   "though this is based on limited, unverified sources") rather than
   presenting the answer as more settled than the evidence supports.
4. If there are sub-questions with no findings at all, briefly note that
   the report is incomplete on those points.

Respond with the summary text only — no heading, no preamble.
"""


def build_writer_prompt(
    original_query: str,
    sub_questions: list[SubQuestion],
    verified_claims: list[VerifiedClaim],
    open_questions: list[str],
) -> str:
    claims_block = (
        "\n".join(f"- [{c.verification_status.value}] {c.claim_text}" for c in verified_claims)
        or "(no claims were found)"
    )
    gaps_block = "\n".join(f"- {q}" for q in open_questions) or "(none)"

    return (
        f"Original research query: {original_query}\n\n"
        f"Sub-questions investigated ({len(sub_questions)} total):\n"
        + "\n".join(f"- {sq.question_text}" for sq in sub_questions)
        + f"\n\nClaims found:\n{claims_block}\n\n"
        f"Sub-questions with no findings:\n{gaps_block}"
    )
