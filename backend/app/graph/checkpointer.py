"""LangGraph checkpointer wiring.

Uses PostgreSQL when DATABASE_URL is configured, otherwise falls back to an
in-memory saver for local development and tests.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row

from app.core.config import settings


@lru_cache(maxsize=1)
def get_checkpointer():
	if not settings.database_url:
		return MemorySaver()

	conn = Connection.connect(
		settings.database_url,
		autocommit=True,
		prepare_threshold=0,
		row_factory=dict_row,
	)
	saver = PostgresSaver(conn)
	saver.setup()
	return saver
