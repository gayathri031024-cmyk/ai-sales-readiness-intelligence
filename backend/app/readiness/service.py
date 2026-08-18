"""
Readiness orchestration.

Reads Phase 8's already-persisted `Evaluation` scores and Phase 5's
already-seeded `ScenarioCompetencyThreshold` rows, runs the pure
`decide_readiness` function (no LLM, no network call, zero cost per
MASTER_PROMPT.md's COST section), and persists one `ReadinessResult` row
per conversation. Never recomputes or calls anything from `evaluation/`
— Phase 8's evaluation step must already have run.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Conversation,
    Evaluation,
    Evidence,
    ReadinessResult,
    Scenario,
    ScenarioCompetencyThreshold,
)
from app.evaluation.extraction import MVP_COMPETENCY_KEYS
from app.evaluation.schemas import EvidenceOut
from app.readiness.decision import CompetencyResult, decide_readiness
from app.readiness.schemas import ConversationResultOut, EvaluationWithThresholdOut, ReadinessOut


class ReadinessServiceError(Exception):
    """Base class for readiness-service errors the API layer translates
    into specific HTTP responses."""


class ConversationNotFoundError(ReadinessServiceError):
    pass


class EvaluationNotFoundError(ReadinessServiceError):
    """Raised when readiness (or the combined result) is requested before
    the conversation has been evaluated — Phase 8's `POST .../evaluate`
    must run first. This module never triggers that step itself, since
    doing so would mean an LLM call from a module that must never make one."""


class ReadinessNotFoundError(ReadinessServiceError):
    """Raised on `GET .../readiness` when no readiness decision has been
    computed yet for an otherwise-valid, evaluated conversation."""


class ThresholdMissingError(ReadinessServiceError):
    """Raised if a competency this conversation was evaluated on has no
    corresponding scenario threshold row. Should never happen against the
    seeded MVP scenario (all 3 MVP competencies always get a threshold) —
    surfaced as an explicit error rather than silently defaulting to 0,
    which would fabricate a threshold every score trivially passes."""


def _load_conversation_full(db: Session, conversation_id: str) -> Conversation | None:
    return (
        db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                joinedload(Conversation.evaluations).joinedload(Evaluation.competency),
                joinedload(Conversation.evaluations)
                .joinedload(Evaluation.evidence)
                .joinedload(Evidence.message),
                joinedload(Conversation.readiness_result),
                joinedload(Conversation.scenario)
                .joinedload(Scenario.thresholds)
                .joinedload(ScenarioCompetencyThreshold.competency),
            )
        )
        .unique()
        .scalar_one_or_none()
    )


def _thresholds_by_key(conversation: Conversation) -> dict[str, int]:
    return {t.competency.key: t.min_score for t in conversation.scenario.thresholds}


def _build_competency_results(conversation: Conversation) -> list[CompetencyResult]:
    thresholds = _thresholds_by_key(conversation)
    results = []
    for evaluation in conversation.evaluations:
        key = evaluation.competency.key
        if key not in thresholds:
            raise ThresholdMissingError(f"No threshold for competency '{key}' on this scenario")
        results.append(
            CompetencyResult(
                competency_key=key,
                display_name=evaluation.competency.display_name,
                score=evaluation.score,
                min_score=thresholds[key],
            )
        )
    return results


def compute_and_persist_readiness(db: Session, conversation_id: str) -> ReadinessResult:
    """Idempotent: returns the existing `readiness_results` row unchanged
    if one already exists (the schema's unique `conversation_id` constraint
    only ever allows one), rather than recomputing. Even though recomputing
    would cost nothing (pure Python), a readiness verdict should reflect
    the evaluation as it stood when first decided, not silently drift on
    a repeat call."""
    conversation = _load_conversation_full(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    if conversation.readiness_result is not None:
        return conversation.readiness_result

    if not conversation.evaluations:
        raise EvaluationNotFoundError(conversation_id)

    thresholds = _thresholds_by_key(conversation)
    results = _build_competency_results(conversation)
    decision = decide_readiness(results)

    readiness = ReadinessResult(
        conversation_id=conversation.id,
        verdict=decision.verdict,
        reasoning=decision.reasoning,
        thresholds_snapshot=thresholds,
    )
    db.add(readiness)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(readiness)
    return readiness


def get_readiness(db: Session, conversation_id: str) -> ReadinessResult:
    conversation = _load_conversation_full(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)
    if conversation.readiness_result is None:
        raise ReadinessNotFoundError(conversation_id)
    return conversation.readiness_result


def get_conversation_result(db: Session, conversation_id: str) -> tuple[Conversation, ReadinessResult]:
    """The combined view the frontend's Result screen needs: evaluation +
    threshold + verdict together. Computes and persists readiness lazily
    if it doesn't exist yet (free — pure Python, no LLM/network cost) as
    long as the conversation has already been evaluated; never triggers
    evaluation itself."""
    readiness = compute_and_persist_readiness(db, conversation_id)
    conversation = _load_conversation_full(db, conversation_id)
    assert conversation is not None  # just loaded successfully above
    return conversation, readiness


def to_readiness_out(readiness: ReadinessResult) -> ReadinessOut:
    return ReadinessOut(
        id=readiness.id,
        conversation_id=readiness.conversation_id,
        verdict=readiness.verdict,
        reasoning=readiness.reasoning,
        computed_at=readiness.computed_at,
    )


def to_conversation_result_out(conversation: Conversation, readiness: ReadinessResult) -> ConversationResultOut:
    thresholds = _thresholds_by_key(conversation)
    ordered = sorted(conversation.evaluations, key=lambda e: MVP_COMPETENCY_KEYS.index(e.competency.key))

    evaluations = [
        EvaluationWithThresholdOut(
            id=e.id,
            competency_key=e.competency.key,
            display_name=e.competency.display_name,
            score=e.score,
            required_min_score=thresholds[e.competency.key],
            diagnosis=e.diagnosis,
            impact=e.impact,
            recommendation=e.recommendation,
            created_at=e.created_at,
            evidence=[
                EvidenceOut(
                    id=ev.id,
                    message_id=ev.message_id,
                    turn_index=ev.message.turn_index,
                    quote=ev.quote,
                    note=ev.note,
                )
                for ev in sorted(e.evidence, key=lambda ev: ev.message.turn_index)
            ],
        )
        for e in ordered
    ]

    return ConversationResultOut(
        conversation_id=conversation.id,
        verdict=readiness.verdict,
        reasoning=readiness.reasoning,
        computed_at=readiness.computed_at,
        evaluations=evaluations,
    )
