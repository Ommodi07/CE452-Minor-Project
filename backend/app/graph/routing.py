"""
Routing functions used as conditional edges in the compiled graph.

Two distinct kinds of routing happen here:

1. Fan-out (`dispatch_researchers`): turns N pending SubQuestions into N
   parallel Researcher invocations via LangGraph's `Send` primitive. This
   runs on the edge FROM planner (and, on a replan loop, potentially again).

2. Fan-in decision (`route_after_critic`): a plain conditional edge that
   inspects critic output + iteration count to decide whether to loop back
   for more research or proceed to the writer.
"""
from __future__ import annotations

from langgraph.graph import END
from langgraph.types import Send

from app.graph.state import GraphState


def dispatch_researchers(state: GraphState) -> list[Send]:
    """
    Fan-out edge: dispatch one Researcher invocation per pending SubQuestion.

    Each Send carries its own scoped state (just `active_sub_question`, plus
    identifiers the researcher needs) rather than the full GraphState, so
    researchers can run truly in parallel without stepping on each other.
    """
    pending = [sq for sq in state.get("sub_questions", []) if sq.status.value != "answered"]

    return [
        Send(
            "researcher",
            {
                "session_id": state["session_id"],
                "original_query": state["original_query"],
                "active_sub_question": sq,
            },
        )
        for sq in pending
    ]


def route_after_critic(state: GraphState) -> str | list[Send]:
    """
    Decide whether to loop back for more research or move to writer.

    Loop guard: once `iteration_count` hits `max_iterations`, always proceed
    to the writer regardless of remaining gaps — unresolved items are carried
    through as `open_questions` / `limitations` instead of looping forever.

    On a loop-back, this re-dispatches Researcher via Send for just the
    sub-questions the Critic flagged (targeted re-research), rather than
    re-running the whole fan-out. Swap this to return "planner" instead if
    you want a full replan on gaps rather than targeted re-research.

    Reflection loop note: critic_node may have set `refined_query` on the
    flagged SubQuestion objects in `state["sub_questions"]` before this edge
    runs (conditional edges see state AFTER the preceding node's return
    value is merged in). Since `retry_targets` pulls those SubQuestion
    objects straight from state, the refined_query rides along automatically
    — Researcher picks it up and searches with it instead of the original
    question_text. No changes needed here for that to work.
    """
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 2)
    flagged_questions = set(state.get("open_questions", []))

    if flagged_questions and iteration_count < max_iterations:
        retry_targets = [
            sq for sq in state.get("sub_questions", []) if sq.question_text in flagged_questions
        ]
        return [
            Send(
                "researcher",
                {
                    "session_id": state["session_id"],
                    "original_query": state["original_query"],
                    "active_sub_question": sq,
                },
            )
            for sq in retry_targets
        ]

    return "writer"


__all__ = ["dispatch_researchers", "route_after_critic", "END"]
