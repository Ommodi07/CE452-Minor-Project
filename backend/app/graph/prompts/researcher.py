"""
Prompt template for the claim-extraction phase of the Researcher node.

Separate step from search itself: search harvests SourceDocs (url, title,
short cited excerpt); this step turns those excerpts into discrete, checkable
Claim objects the Critic can later verify or dispute.
"""
from __future__ import annotations

from app.models.schemas import SourceDoc, SubQuestion

CLAIM_SYSTEM_PROMPT = """You are the claim-extraction step of a Researcher agent in a multi-agent research system.

You will be given one sub-question and a list of source documents (each
with a url, title, and a short excerpt). Your job is to extract discrete,
checkable factual claims from these excerpts that help answer the
sub-question.

Rules:
1. Every claim must be traceable to exactly one source's excerpt. Set
   `source_url` to that source's exact url (copy it verbatim from the list
   you were given — do not alter or invent urls).
2. Do not extract claims that aren't supported by the given excerpt text.
   If an excerpt doesn't contain anything answering the sub-question, skip
   it rather than inventing a claim.
3. Extract at most 2 claims per source — pick the most relevant ones.
4. `confidence` (0.0-1.0) reflects how directly and unambiguously the
   excerpt supports the claim, not how important the claim is.
5. `supporting_excerpt` should be a short quote or close paraphrase from the
   source excerpt you were given — not the full excerpt restated.

Call the `emit_claims` tool exactly once with your final answer. If none of
the sources support any claims, call it with an empty `claims` array.
"""


def build_claim_extraction_prompt(sub_question: SubQuestion, source_docs: list[SourceDoc]) -> str:
    sources_block = "\n\n".join(
        f'- url: {doc.url}\n  title: {doc.title}\n  excerpt: "{doc.snippet}"' for doc in source_docs
    )
    return (
        f"Sub-question: {sub_question.question_text}\n\n"
        f"Sources:\n{sources_block}"
    )
