"""
Shared state schema passed between every node in the research graph.

Only `source_docs` and `claims` use an additive reducer (`operator.add`)
because they are the two fields written concurrently by parallel Researcher
invocations (fanned out via LangGraph's `Send`). Every other field is written
by exactly one node at a time, so plain last-write-wins is safe and simpler.
"""
from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from app.models.schemas import Claim, Report, SourceDoc, SubQuestion, VerifiedClaim

GraphStatus = Literal[
    "planning", "researching", "critiquing", "writing", "done", "error"
]


class GraphState(TypedDict, total=False):
    # --- run identity / input ---
    session_id: str
    original_query: str

    # --- planning ---
    sub_questions: list[SubQuestion]

    # Set only on the per-dispatch state handed to an individual Researcher
    # invocation via Send(); not present on the "main" graph state.
    active_sub_question: SubQuestion

    # --- research (written concurrently across fanned-out Researcher nodes) ---
    source_docs: Annotated[list[SourceDoc], operator.add]
    claims: Annotated[list[Claim], operator.add]

    # --- critique ---
    verified_claims: list[VerifiedClaim]
    critic_feedback: list[str]
    open_questions: list[str]

    # --- control flow ---
    iteration_count: int
    max_iterations: int
    status: GraphStatus
    errors: Annotated[list[str], operator.add]

    # --- output ---
    report: Report | None


def initial_state(
    session_id: str, query: str, max_iterations: int = 2
) -> GraphState:
    """Build the starting state for a new graph run."""
    return GraphState(
        session_id=session_id,
        original_query=query,
        sub_questions=[],
        source_docs=[],
        claims=[],
        verified_claims=[],
        critic_feedback=[],
        open_questions=[],
        iteration_count=0,
        max_iterations=max_iterations,
        status="planning",
        errors=[],
        report=None,
    )
