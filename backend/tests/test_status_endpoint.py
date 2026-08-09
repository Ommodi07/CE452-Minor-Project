from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_status_endpoint_lists_routes_and_connections(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "database_url", "sqlite+pysqlite:///:memory:")
    monkeypatch.setattr(settings, "chroma_path", None)

    import app.api.routes.status as status_module

    async def fake_gemini_check():
        return status_module._CheckResult(active=True, configured=True, details="Gemini API reachable.")

    monkeypatch.setattr(status_module, "_check_gemini_api", fake_gemini_check)

    response = client.get("/status")

    assert response.status_code == 200
    payload = response.json()

    assert payload["app_name"] == settings.app_name
    assert payload["overall_ok"] is True

    endpoints = {item["path"]: item for item in payload["endpoints"]}
    assert "/health" in endpoints
    assert endpoints["/research"]["description"].startswith("Run the research graph")
    assert endpoints["/status"]["active"] is True

    connections = {item["name"]: item for item in payload["connections"]}
    assert connections["gemini_api"]["active"] is True
    assert connections["database"]["active"] is True
    assert connections["vector_store"]["active"] is False
    assert connections["report_store"]["active"] is True
    assert connections["session_store"]["active"] is True