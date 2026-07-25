from app.models.schemas import Report
from app.services.report_store import InMemoryReportStore, get_report_store


def _report(session_id="s1") -> Report:
    return Report(session_id=session_id, title="T", executive_summary="S")


def test_save_and_get_round_trip():
    store = InMemoryReportStore()
    report = _report()
    store.save("job1", report)
    assert store.get("job1") is report


def test_get_returns_none_for_unknown_job_id():
    store = InMemoryReportStore()
    assert store.get("does-not-exist") is None


def test_save_overwrites_existing_entry_for_same_job_id():
    store = InMemoryReportStore()
    store.save("job1", _report(session_id="first"))
    store.save("job1", _report(session_id="second"))
    assert store.get("job1").session_id == "second"


def test_get_report_store_returns_same_singleton_instance():
    assert get_report_store() is get_report_store()
