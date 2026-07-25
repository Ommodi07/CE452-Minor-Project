"""
/research routes.

For this skeleton, POST /research runs the graph synchronously to
completion and returns the final Report. Once streaming is wired up
(app/api/routes/stream.py), prefer POST /research to *start* a run and
GET/WS /stream/{session_id} to watch node-by-node progress instead of
blocking on the full ainvoke().

The completed Report is also saved to the report store, keyed by
session_id — this is what lets GET /research/{job_id}/export (see
app/api/routes/export.py) retrieve it later. `job_id` and `session_id` are
the same value today; kept as distinct names in the URL/store interface in
case they diverge later (e.g. one session producing multiple export jobs).
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from app.api.deps import get_graph
from app.core.config import settings
from app.graph.state import initial_state
from app.models.schemas import Report
from app.services.report_store import get_report_store
from app.services.session_store import get_session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The research question to investigate.")
    session_id: str | None = Field(
        default=None, description="Optional client-supplied session id; generated if omitted."
    )
    max_iterations: int | None = Field(
        default=None, description="Override the default critic re-research loop cap."
    )


class ResearchResponse(BaseModel):
    session_id: str
    status: str
    report: Report | None = None
    open_questions: list[str] = []
    errors: list[str] = []


@router.post("", response_model=ResearchResponse)
async def run_research(request: ResearchRequest, graph=Depends(get_graph)) -> ResearchResponse:
    session_id = request.session_id or uuid.uuid4().hex

    start_state = initial_state(
        session_id=session_id,
        query=request.query,
        max_iterations=request.max_iterations or settings.default_max_iterations,
    )

    try:
        final_state = await graph.ainvoke(
            start_state,
            config={"configurable": {"thread_id": session_id}},
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to client as 500 below
        logger.exception("Graph run failed for session_id=%s", session_id)
        raise HTTPException(status_code=500, detail=f"Research run failed: {exc}") from exc

    report = final_state.get("report")
    if report is not None:
        get_report_store().save(session_id, report)

    get_session_store().save(session_id, jsonable_encoder(final_state))

    return ResearchResponse(
        session_id=session_id,
        status=final_state.get("status", "error"),
        report=report,
        open_questions=final_state.get("open_questions", []),
        errors=final_state.get("errors", []),
    )
