"""PostgreSQL repository for persisting/retrieving finished Reports."""
from __future__ import annotations

from app.db.models import ReportRecord
from app.db.session import get_session_factory
from app.models.schemas import Report


class ReportRepo:
    def save(self, job_id: str, report: Report) -> None:
        record = ReportRecord(job_id=job_id, report_json=report.model_dump(mode="json"))
        session_factory = get_session_factory()
        with session_factory() as db:
            db.merge(record)
            db.commit()

    def get(self, report_id: str) -> Report | None:
        session_factory = get_session_factory()
        with session_factory() as db:
            record = db.get(ReportRecord, report_id)
            if record is None:
                return None
            return Report.model_validate(record.report_json)
