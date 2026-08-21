"""
Builds the EmbeddingProvider production code should use, from
`Settings` (env var EMBEDDING_PROVIDER / EMBEDDING_MODEL — see
core/config.py). Same "tests never call this — they construct a
provider directly" split as app/ai/factory.py.
"""
from __future__ import annotations

from app.ai.embedding_provider import (
    EmbeddingProvider,
    HashingEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
)
from app.core.config import Settings, get_settings


def build_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    if settings.embedding_provider == "sentence_transformer":
        return SentenceTransformerEmbeddingProvider(model_name=settings.embedding_model)
    return HashingEmbeddingProvider()
