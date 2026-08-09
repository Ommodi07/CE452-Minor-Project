from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import export, research, sessions, status, stream
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router)
app.include_router(export.router)
app.include_router(sessions.router)
app.include_router(status.router)
app.include_router(stream.router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
