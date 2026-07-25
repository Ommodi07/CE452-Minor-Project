"""
Live graph-progress streaming — placeholder.

TODO: use graph.astream(start_state, stream_mode="updates") inside an
EventSourceResponse (sse-starlette) so the Next.js graph-visualizer
component can highlight the active node in real time, keyed by
`status` in GraphState. Not implemented in this skeleton.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/{session_id}")
async def stream_progress(session_id: str):
    raise HTTPException(status_code=501, detail="Streaming not yet implemented.")
