"""
Builds and compiles the research graph:

    START -> planner -> (fan-out via Send) -> researcher(s) -> critic
                                                                   |
                                        (conditional: gaps?) ------+------> writer -> END
                                                 |
                                                 +--> back to researcher (targeted re-research)

Import `get_compiled_graph()` from here anywhere you need to run the graph
(e.g. the /research API route). The graph is built once and cached.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.critic import critic_node
from app.graph.checkpointer import get_checkpointer
from app.graph.nodes.planner import planner_node
from app.graph.nodes.researcher import researcher_node
from app.graph.nodes.writer import writer_node
from app.graph.routing import dispatch_researchers, route_after_critic
from app.graph.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("critic", critic_node)
    graph.add_node("writer", writer_node)

    graph.add_edge(START, "planner")

    # Fan-out: planner -> N parallel researcher invocations (one per SubQuestion)
    graph.add_conditional_edges("planner", dispatch_researchers, ["researcher"])

    # Fan-in: LangGraph automatically joins all parallel "researcher" branches
    # before running "critic" once, since critic has a static incoming edge.
    graph.add_edge("researcher", "critic")

    # Fan-out again (targeted retry) OR proceed to writer.
    graph.add_conditional_edges("critic", route_after_critic, ["researcher", "writer"])

    graph.add_edge("writer", END)

    return graph


@lru_cache(maxsize=1)
def get_compiled_graph():
    """
    Compile once and reuse across requests. Pass a `checkpointer=` here
    (see app/graph/checkpointer.py, not yet implemented) once you want
    resumable/inspectable runs persisted to Postgres.
    """
    return build_graph().compile(checkpointer=get_checkpointer())
