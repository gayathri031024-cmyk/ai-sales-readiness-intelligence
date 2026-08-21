"""
Deterministic verification of proposed coaching points — the Phase 10
analogue of Phase 8's `evaluation/verification.py`.

The invariant this module enforces:

    A coaching point cannot be persisted if it cites an evidence_id that
    isn't a real, already-verified piece of evidence for the competency
    it claims to be about.

Pure Python, no LLM, no DB session — takes the model's proposed points
and the actual (competency_key -> valid evidence ids) map built from
already-persisted `Evidence` rows, and returns only the points that
survive. A point citing a nonexistent id is dropped entirely rather than
persisted with a dangling/fabricated reference; a point with no
evidence_id at all (general coaching, or coaching about a competency
with no evidence) always passes through unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.coaching.generation import CoachingPointCandidate
from app.evaluation.extraction import CompetencyKey


@dataclass(frozen=True)
class VerifiedCoachingPoint:
    competency_key: CompetencyKey
    evidence_id: str | None
    message: str


def verify_coaching_points(
    candidates: list[CoachingPointCandidate],
    valid_evidence_ids_by_competency: dict[str, set[str]],
    evaluated_competency_keys: set[str],
) -> list[VerifiedCoachingPoint]:
    """Keeps only points that pass every grounding check:

    1. `competency_key` is one this conversation actually has an
       evaluation for (guards against a stale/foreign key slipping
       through even though the schema's `Literal` already constrains the
       value space).
    2. `evidence_id`, if present, is an id this module was actually
       handed for that exact competency — i.e. a real `Evidence` row
       already proven grounded by Phase 8's own verification step. A
       null `evidence_id` always passes (nothing to check).

    A candidate failing either check is silently dropped, never
    persisted — this function never raises; a bad candidate is a normal,
    expected outcome of an LLM proposing coaching, not an error.
    """
    verified: list[VerifiedCoachingPoint] = []

    for candidate in candidates:
        if candidate.competency_key not in evaluated_competency_keys:
            continue

        if candidate.evidence_id is not None:
            valid_ids = valid_evidence_ids_by_competency.get(candidate.competency_key, set())
            if candidate.evidence_id not in valid_ids:
                continue

        verified.append(
            VerifiedCoachingPoint(
                competency_key=candidate.competency_key,
                evidence_id=candidate.evidence_id,
                message=candidate.message,
            )
        )

    return verified
