"""Report persistence, backed by PostgreSQL when configured.

Falls back to an in-memory store for local development or test runs without
DATABASE_URL so the rest of the app can keep using the same save/get API.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.db.repositories.report_repo import ReportRepo
from app.db.session import init_db
from app.models.schemas import Report


class InMemoryReportStore:
    def __init__(self):
        self._reports: dict[str, Report] = {}

    def save(self, job_id: str, report: Report) -> None:
        self._reports[job_id] = report

    def get(self, job_id: str) -> Report | None:
        return self._reports.get(job_id)


class PostgresReportStore:
    def __init__(self):
        init_db()
        self._repo = ReportRepo()

    def save(self, job_id: str, report: Report) -> None:
        self._repo.save(job_id, report)

    def get(self, job_id: str) -> Report | None:
        return self._repo.get(job_id)


@lru_cache(maxsize=1)
def get_report_store() -> InMemoryReportStore | PostgresReportStore:
    if settings.database_url:
        return PostgresReportStore()
    return InMemoryReportStore()
