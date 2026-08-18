"""Application status and connectivity endpoints."""
from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_engine
from app.services.gemini_api import GeminiAPIClient
from app.services.report_store import get_report_store
from app.services.session_store import get_session_store
from app.tools.vector_store import get_vector_store

router = APIRouter(tags=["status"])

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class ApiEndpointStatus(BaseModel):
    method: str
    path: str
    description: str
    active: bool


class ConnectionStatus(BaseModel):
    name: str
    active: bool
    configured: bool = True
    details: str = ""


class StatusResponse(BaseModel):
    app_name: str
    environment: str
    endpoints: list[ApiEndpointStatus]
    connections: list[ConnectionStatus]
    overall_ok: bool


@dataclass(slots=True)
class _CheckResult:
    active: bool
    configured: bool
    details: str = ""


def _endpoint_inventory() -> list[ApiEndpointStatus]:
    return [
        ApiEndpointStatus(
            method="GET",
            path="/health",
            description="Basic service health check.",
            active=True,
        ),
        ApiEndpointStatus(
            method="POST",
            path="/research",
            description="Run the research graph and persist the completed report.",
            active=True,
        ),
        ApiEndpointStatus(
            method="GET",
            path="/research/{job_id}/export",
            description="Download a completed research report as a DOCX file.",
            active=True,
        ),
        ApiEndpointStatus(
            method="POST",
            path="/sessions",
            description="Create a new research session.",
            active=True,
        ),
        ApiEndpointStatus(
            method="GET",
            path="/sessions/{session_id}",
            description="Fetch a stored session state by session id.",
            active=True,
        ),
        ApiEndpointStatus(
            method="GET",
            path="/stream/{session_id}",
            description="Streaming progress placeholder for a research session.",
            active=True,
        ),
        ApiEndpointStatus(
            method="GET",
            path="/status",
            description="List API routes and connection checks for the backend.",
            active=True,
        ),
    ]


async def _check_gemini_api() -> _CheckResult:
    client = GeminiAPIClient()
    if not client.is_configured or not client.api_key:
        return _CheckResult(active=False, configured=False, details="GEMINI_API_KEY is not configured.")

    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.get(
                f"{_GEMINI_BASE_URL}/models",
                params={"key": client.api_key},
            )
            response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - surfaced in status payload
        return _CheckResult(active=False, configured=True, details=f"Gemini API check failed: {exc}")

    return _CheckResult(active=True, configured=True, details="Gemini API reachable.")


def _check_database() -> _CheckResult:
    if not settings.database_url:
        return _CheckResult(active=False, configured=False, details="DATABASE_URL is not configured.")

    try:
        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - surfaced in status payload
        return _CheckResult(active=False, configured=True, details=f"Database check failed: {exc}")

    return _CheckResult(active=True, configured=True, details="Database connection is healthy.")


def _check_vector_store() -> _CheckResult:
    if not settings.chroma_path:
        return _CheckResult(active=False, configured=False, details="CHROMA_PATH is not configured.")

    try:
        store = get_vector_store()
    except Exception as exc:  # noqa: BLE001 - surfaced in status payload
        return _CheckResult(active=False, configured=True, details=f"Vector store check failed: {exc}")

    if store is None:
        return _CheckResult(active=False, configured=False, details="Vector store is not available.")

    return _CheckResult(active=True, configured=True, details="Vector store is ready.")


def _check_state_stores() -> list[ConnectionStatus]:
    using_postgres = bool(settings.database_url)

    report_status = ConnectionStatus(
        name="report_store",
        active=True,
        configured=using_postgres,
        details="Using PostgreSQL-backed store." if using_postgres else "Using in-memory store.",
    )
    session_status = ConnectionStatus(
        name="session_store",
        active=True,
        configured=using_postgres,
        details="Using PostgreSQL-backed store." if using_postgres else "Using in-memory store.",
    )

    try:
        get_report_store()
    except Exception as exc:  # noqa: BLE001 - surfaced in status payload
        report_status.active = False
        report_status.details = f"Store initialization failed: {exc}"

    try:
        get_session_store()
    except Exception as exc:  # noqa: BLE001 - surfaced in status payload
        session_status.active = False
        session_status.details = f"Store initialization failed: {exc}"

    return [
        report_status,
        session_status,
    ]


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    connections = []

    gemini = await _check_gemini_api()
    connections.append(
        ConnectionStatus(
            name="gemini_api",
            active=gemini.active,
            configured=gemini.configured,
            details=gemini.details,
        )
    )

    database = _check_database()
    connections.append(
        ConnectionStatus(
            name="database",
            active=database.active,
            configured=database.configured,
            details=database.details,
        )
    )

    vector_store = _check_vector_store()
    connections.append(
        ConnectionStatus(
            name="vector_store",
            active=vector_store.active,
            configured=vector_store.configured,
            details=vector_store.details,
        )
    )

    connections.extend(_check_state_stores())

    overall_ok = all(item.active for item in connections)

    return StatusResponse(
        app_name=settings.app_name,
        environment=settings.environment,
        endpoints=_endpoint_inventory(),
        connections=connections,
        overall_ok=overall_ok,
    )