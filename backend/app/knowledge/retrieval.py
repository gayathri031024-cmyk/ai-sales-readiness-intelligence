"""
Deterministic retrieval — pure Python cosine similarity over already-
persisted chunk embeddings. No vector database: per DECISIONS.md
(Phase 13) this runs in-process, which is appropriate at MVP scale (a
handful of short product documents), with pgvector deferred to
Phase 21 deployment when both real Postgres and a larger corpus
justify it (see ARCHITECTURE.md §10, DATA_MODEL.md §3).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

DEFAULT_TOP_K = 4
DEFAULT_MIN_SIMILARITY = 0.15


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_title: str
    text: str
    similarity: float


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Vectors must be the same length to compare.")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_top_k(
    query_vector: list[float],
    candidates: list[tuple[str, str, str, str, list[float]]],
    *,
    top_k: int = DEFAULT_TOP_K,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> list[RetrievedChunk]:
    """`candidates` is (chunk_id, document_id, document_title, text,
    embedding) tuples — deliberately not ORM rows, so this stays pure
    and independently testable without a DB session, same posture as
    readiness/decision.py and difficulty/decision.py."""
    scored = [
        RetrievedChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            document_title=document_title,
            text=text,
            similarity=cosine_similarity(query_vector, embedding),
        )
        for chunk_id, document_id, document_title, text, embedding in candidates
    ]
    scored = [c for c in scored if c.similarity >= min_similarity]
    scored.sort(key=lambda c: c.similarity, reverse=True)
    return scored[:top_k]
