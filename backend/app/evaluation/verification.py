"""
Deterministic evidence verification (ARCHITECTURE.md §4B's boundary
between "the LLM may propose" and "deterministic validation must
prevent fabricated evidence" — this file is the second half).

The invariant this module exists to enforce:

    An evidence item cannot be persisted as valid evidence unless it is
    supported by the actual transcript.

Deliberately pure Python, no LLM call, no DB session — takes the actual
transcript messages and the model's proposed candidates, and returns
only the candidates that are provably grounded. This mirrors the
project's existing pattern of keeping the "propose vs. decide" boundary
enforceable in code (see DECISIONS.md, Phase 1, on the readiness engine
being deterministic for the same reason).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.evaluation.extraction import CompetencyKey, EvidenceCandidate


@dataclass(frozen=True)
class VerifiedEvidence:
    """A candidate that survived grounding — safe to persist."""

    message_id: str
    turn_index: int
    competency_key: CompetencyKey
    quote: str
    note: str | None


@dataclass(frozen=True)
class TranscriptMessage:
    """Minimal, verification-facing view of a `Message` ORM row — avoids
    coupling this pure module to SQLAlchemy. `service.py` builds these
    from real `Message` objects before calling `verify_evidence`."""

    id: str
    turn_index: int
    sender: str
    content: str


def _normalize(text: str) -> str:
    """Whitespace/case-insensitive comparison only — quotes must still be
    the rep's actual words, but we don't fail a true positive over a
    trivial whitespace or capitalization difference the model introduced
    while copying."""
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_evidence(
    candidates: list[EvidenceCandidate],
    messages: list[TranscriptMessage],
) -> list[VerifiedEvidence]:
    """Keeps only candidates that pass every grounding check:

    1. `turn_index` refers to a message that actually exists in this
       conversation.
    2. That message's sender is "rep" — evidence of the rep's competency
       can never be grounded in something the buyer said (see
       extraction.py's system prompt, which already instructs the model
       not to do this; this is the deterministic backstop, not the only
       control).
    3. `quote` is an actual (whitespace/case-normalized) substring of
       that message's real content — not paraphrased, not invented.

    A candidate failing any check is silently dropped, never persisted,
    per the module-level invariant above. This function never raises —
    a bad candidate is a normal, expected outcome of an LLM proposing
    evidence, not an error condition.
    """
    by_turn_index = {m.turn_index: m for m in messages}
    verified: list[VerifiedEvidence] = []

    for candidate in candidates:
        message = by_turn_index.get(candidate.turn_index)
        if message is None:
            continue  # references a turn that doesn't exist — hallucinated
        if message.sender != "rep":
            continue  # can't ground rep-competency evidence in a buyer line
        if _normalize(candidate.quote) not in _normalize(message.content):
            continue  # quote wasn't actually said — hallucinated

        verified.append(
            VerifiedEvidence(
                message_id=message.id,
                turn_index=message.turn_index,
                competency_key=candidate.competency_key,
                quote=candidate.quote,
                note=candidate.note,
            )
        )

    return verified
