"""SQLAlchemy session factory for the PostgreSQL-backed stores."""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.models import Base


@lru_cache(maxsize=1)
def get_engine():
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL not configured.")
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())
