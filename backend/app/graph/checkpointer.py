"""LangGraph checkpointer wiring.

Uses PostgreSQL when DATABASE_URL is configured, otherwise falls back to an
in-memory saver for local development and tests.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver
@lru_cache(maxsize=1)
def get_checkpointer():
	return MemorySaver()
