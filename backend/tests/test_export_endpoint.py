from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Report, ReportSection, SourceDoc
from app.services.report_store import get_report_store

client = TestClient(app)


def _report_with_content() -> Report:
    doc = SourceDoc(sub_question_id="sq1", url="https://reuters.com/a", title="Reuters Article", snippet="s")
    return Report(
        session_id="job-export-test",
        title="Test Export Report",
        executive_summary="Summary.",
        sections=[ReportSection(heading="H1", content="- A claim [1]", cited_claim_ids=[])],
        citations={doc.id: doc},
    )


def test_export_returns_404_for_unknown_job_id():
    response = client.get("/research/does-not-exist/export")
    assert response.status_code == 404
    assert "does-not-exist" in response.json()["detail"]


def test_export_returns_valid_docx_for_known_job_id():
    get_report_store().save("job-export-test", _report_with_content())

    response = client.get("/research/job-export-test/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert 'filename="research-report-job-export-test.docx"' in response.headers["content-disposition"]
    assert response.content[:2] == b"PK"  # valid docx/zip


def test_export_docx_content_matches_report():
    get_report_store().save("job-export-test-2", _report_with_content())

    response = client.get("/research/job-export-test-2/export")

    import io
    from docx import Document
    document = Document(io.BytesIO(response.content))
    all_text = "\n".join(p.text for p in document.paragraphs)
    assert "Test Export Report" in all_text
    assert "A claim" in all_text
    assert "Reuters Article" in all_text
