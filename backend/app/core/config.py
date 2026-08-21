"""
Application configuration.

Reads from environment variables / .env. Never hardcode secrets here.

Phase 3 note: DATABASE_URL defaults to a local SQLite file so the
foundation can be verified without a running Postgres instance.
Production (Phase 21) points this at a real Postgres DSN — no code
change required, since SQLAlchemy handles both via the same engine
creation path.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "AI Sales Readiness Intelligence"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./dev.db"

    # Populated in later phases (Phase 6+) once the AI layer is built.
    llm_api_key: str | None = None
    llm_model: str = "not-configured"

    # Phase 13 — embedding provider for Product RAG. "hashing" is the
    # zero-dependency, zero-network deterministic default (see
    # app/ai/embedding_provider.py); set to "sentence_transformer" to
    # use a real local open-source embedding model instead. Never an
    # external embedding API, per DECISIONS.md (Phase 13).
    embedding_provider: str = "hashing"
    embedding_model: str = "all-MiniLM-L6-v2"


@lru_cache
def get_settings() -> Settings:
    return Settings()
