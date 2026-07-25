from __future__ import annotations

from app.graph.graph import get_compiled_graph


def get_graph():
    """FastAPI dependency returning the compiled, cached LangGraph graph."""
    return get_compiled_graph()
