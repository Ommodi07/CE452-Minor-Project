"""Session management routes backed by the configured session store."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.session_store import get_session_store

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreateResponse(BaseModel):
    session_id: str


class SessionResponse(BaseModel):
    session_id: str
    state: dict


@router.post("", response_model=SessionCreateResponse)
async def create_session() -> SessionCreateResponse:
    session_id = uuid.uuid4().hex
    get_session_store().save(session_id, {"session_id": session_id, "status": "created"})
    return SessionCreateResponse(session_id=session_id)


@router.get("/{session_id}")
async def get_session(session_id: str) -> SessionResponse:
    state = get_session_store().get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionResponse(session_id=session_id, state=state)
