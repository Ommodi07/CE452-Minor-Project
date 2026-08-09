"""
/research/{job_id}/export route.

Looks up the Report saved by POST /research (see research.py) and returns
it as a downloadable .docx. 404s if the job_id is unknown or the run hasn't
produced a report yet (e.g. it's still in progress, or failed before
reaching the writer).
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.docx_export import render_report_to_docx
from app.services.report_store import get_report_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/research", tags=["export"])

_DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

@router.get("/{job_id}/export")
async def export_report(job_id: str) -> Response:
    report = get_report_store().get(job_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for job_id={job_id!r}. Has the research run completed?",
        )

    try:
        # render_report_to_docx is synchronous/CPU-bound (python-docx has no
        # async API) — run it off the event loop so one export request
        # doesn't stall other concurrent requests this worker is handling.
        docx_bytes = await asyncio.to_thread(render_report_to_docx, report)
    except Exception as exc:  # noqa: BLE001
        logger.exception("DOCX export failed for job_id=%s", job_id)
        raise HTTPException(status_code=500, detail=f"DOCX export failed: {exc}") from exc

    filename = f"research-report-{job_id}.docx"
    return Response(
        content=docx_bytes,
        media_type=_DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
