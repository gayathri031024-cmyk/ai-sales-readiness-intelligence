"""
Embedding provider abstraction — the Phase 13 analogue of
app/ai/provider.py's LLMProvider split.

Why this exists: Phase 13 needs to turn text into vectors for
similarity search. Per DECISIONS.md (Phase 13), embeddings run
entirely locally — no external embedding API — mirroring the same
"deterministic/local over networked API" cost posture used everywhere
else in this project (MASTER_PROMPT.md's COST section: "prefer
deterministic logic over LLM calls wherever possible... design for
cheap development and demo"). Production code depends on
`EmbeddingProvider`, never a concrete implementation directly — same
swappability contract as `LLMProvider`.

`HashingEmbeddingProvider` is a zero-dependency, zero-network, fully
deterministic bag-of-words feature-hashing vectorizer. It is what test
discipline requires (no model download, no flake, byte-identical
output across runs — same posture as `MockLLMProvider`) and is also a
legitimate lightweight default for the current MVP-scale knowledge
base (a handful of short product documents).

`SentenceTransformerEmbeddingProvider` wraps a real local open-source
embedding model for genuinely semantic similarity, entirely offline
after a one-time model download — never a per-request network call, so
it is still "no external API." Like `AnthropicProvider` (see
KNOWN_ISSUES.md), it is not exercised in automated tests here.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Protocol


class EmbeddingUnavailableError(Exception):
    """Raised when a provider cannot produce an embedding at all.
    Callers must catch this and degrade gracefully, same contract as
    LLMUnavailableError."""


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed(self, text: str) -> list[float]:
        """Return a fixed-length vector, or raise EmbeddingUnavailableError."""
        ...


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class HashingEmbeddingProvider:
    """Deterministic, dependency-free embedding via the hashing trick:
    each token is hashed into one of `dimensions` buckets, term
    frequency accumulated, then the vector is L2-normalized so cosine
    similarity behaves sensibly. The same text always produces the
    exact same vector — no model, no network, no randomness. `calls`
    records every embedded string, mirroring `MockLLMProvider.calls`,
    so tests can assert on embedding call counts if ever needed."""

    dimensions: int = 256
    calls: list[str] = field(default_factory=list)

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        vector = [0.0] * self.dimensions
        tokens = _tokenize(text)
        if not tokens:
            return vector
        for token in tokens:
            bucket = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % self.dimensions
            vector[bucket] += 1.0
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]


class SentenceTransformerEmbeddingProvider:
    """Production provider: a real local open-source embedding model
    (sentence-transformers, e.g. all-MiniLM-L6-v2). Downloaded once,
    runs fully offline thereafter. Constructing this class never
    touches the model; only the first real `embed()` call loads it —
    same laziness posture as `AnthropicProvider._get_client()`."""

    dimensions = 384  # all-MiniLM-L6-v2 output size

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # local import
            except ImportError as exc:
                raise EmbeddingUnavailableError(
                    "sentence-transformers is not installed — cannot load a local "
                    "embedding model. Install it, or set EMBEDDING_PROVIDER=hashing."
                ) from exc
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        try:
            model = self._get_model()
            vector = model.encode(text, normalize_embeddings=True)
            return vector.tolist()
        except EmbeddingUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 — same broad-catch posture as AnthropicProvider
            raise EmbeddingUnavailableError(f"Local embedding model failed: {exc}") from exc
