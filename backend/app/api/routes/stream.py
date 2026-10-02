"""SSE endpoint for the final persisted research result."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services.report_store import get_report_store
from app.services.session_store import get_session_store

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/{session_id}")
async def stream_progress(session_id: str):
    async def events():
        for _ in range(120):
            state = get_session_store().get(session_id)
            report = get_report_store().get(session_id)
            if state is not None:
                status = state.get("status", "running")
                if status == "done":
                    status = "completed"
                payload = {
                    "session_id": session_id,
                    "status": status,
                    "report_ready": report is not None,
                    "report": report.model_dump(mode="json") if report is not None else None,
                    "open_questions": state.get("open_questions", []),
                    "errors": state.get("errors", []),
                }
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                if report is not None and status in {"completed", "fallback"}:
                    yield f"event: complete\ndata: {json.dumps(payload)}\n\n"
                    return
            else:
                yield f"event: progress\ndata: {json.dumps({'session_id': session_id, 'status': 'waiting', 'report_ready': False})}\n\n"
            await asyncio.sleep(1)

        yield f"event: error\ndata: {json.dumps({'session_id': session_id, 'status': 'timeout', 'report_ready': False})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
