"""
Deterministic text chunking — pure Python, no LLM, no network.

Splits a document's raw text into overlapping fixed-size character
chunks, breaking on paragraph/sentence boundaries where reasonably
possible so a chunk doesn't split mid-sentence more than necessary.
Deterministic: the same input text always produces the exact same
chunks, in the same order, every time (asserted directly in tests).
"""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 150


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str


def chunk_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    normalized = text.strip()
    if not normalized:
        return []

    chunks: list[Chunk] = []
    start = 0
    length = len(normalized)
    index = 0

    while start < length:
        end = min(start + chunk_size, length)
        # Prefer breaking at the last paragraph/sentence boundary inside
        # the window, so a chunk doesn't split mid-sentence when a
        # cleaner break point is available.
        if end < length:
            boundary = _last_boundary(normalized, start, end)
            if boundary is not None and boundary > start:
                end = boundary

        piece = normalized[start:end].strip()
        if piece:
            chunks.append(Chunk(index=index, text=piece))
            index += 1

        if end >= length:
            break
        # Always make forward progress even if overlap would otherwise
        # push start backward past a very short chunk.
        start = max(end - overlap, start + 1)

    return chunks


def _last_boundary(text: str, start: int, end: int) -> int | None:
    window = text[start:end]
    for marker in ("\n\n", ". ", "\n"):
        pos = window.rfind(marker)
        if pos != -1:
            return start + pos + len(marker)
    return None
