from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Research Analyst"
    environment: str = "development"

    # CORS
    frontend_origin: str = "http://localhost:3000"

    # LLM provider config.
    gemini_api_key: str | None = None
    default_model: str = "gemini-2.0-flash"
    embedding_model: str = "text-embedding-004"

    # Vector store
    chroma_path: str | None = None
    chroma_collection: str = "research_sources"

    # Graph run limits
    default_max_iterations: int = 2

    # Persistence (placeholder — used once checkpointer.py / DB repos are implemented)
    database_url: str | None = None

settings = Settings()
