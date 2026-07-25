"""Session persistence wrapper mirroring the report store contract."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.db.repositories.session_repo import SessionRepo
from app.db.session import init_db


class InMemorySessionStore:
    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def save(self, session_id: str, state: dict) -> None:
        self._sessions[session_id] = state

    def get(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)


class PostgresSessionStore:
    def __init__(self):
        init_db()
        self._repo = SessionRepo()

    def save(self, session_id: str, state: dict) -> None:
        self._repo.save(session_id, state)

    def get(self, session_id: str) -> dict | None:
        return self._repo.get(session_id)


@lru_cache(maxsize=1)
def get_session_store() -> InMemorySessionStore | PostgresSessionStore:
    if settings.database_url:
        return PostgresSessionStore()
    return InMemorySessionStore()