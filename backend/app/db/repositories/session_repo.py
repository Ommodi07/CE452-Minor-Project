"""PostgreSQL repository for persisting/retrieving GraphState snapshots per session."""
from __future__ import annotations

from app.db.models import SessionRecord
from app.db.session import get_session_factory


class SessionRepo:
    def save(self, session_id: str, state: dict) -> None:
        record = SessionRecord(session_id=session_id, state_json=state)
        session_factory = get_session_factory()
        with session_factory() as db:
            db.merge(record)
            db.commit()

    def get(self, session_id: str) -> dict | None:
        session_factory = get_session_factory()
        with session_factory() as db:
            record = db.get(SessionRecord, session_id)
            if record is None:
                return None
            return dict(record.state_json)
