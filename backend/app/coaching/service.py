"""
Coaching orchestration (Phase 10).

Reads Phase 8's already-persisted `Evaluation`/`Evidence` rows and Phase
9's already-persisted `ReadinessResult`, runs the pure `pick_priority`
function (no LLM), then calls `generate_coaching` (one LLM call,
constrained to only this already-verified data) and `verify_coaching_points`
(deterministic grounding — drops any point citing an evidence id that
wasn't actually shown to the model) before persisting one `CoachingSession`
row per conversation. Never triggers evaluation or readiness itself —
both must already exist, same "propose vs. decide, and never silently
compute a prerequisite step" discipline as `readiness/service.py`.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.ai.provider import LLMProvider
from app.coaching.generation import generate_coaching
from app.coaching.priority import NoCompetencyResultsError as PriorityNoCompetencyResultsError
from app.coaching.priority import PriorityPick, pick_priority
from app.coaching.schemas import CoachingPointOut, CoachingSessionOut
from app.coaching.verification import verify_coaching_points
from app.db.models import (
    CoachingSession,
    Conversation,
    Evaluation,
    Evidence,
    Scenario,
    ScenarioCompetencyThreshold,
)
from app.evaluation.extraction import MVP_COMPETENCY_KEYS
from app.readiness.decision import CompetencyResult


class CoachingServiceError(Exception):
    """Base class for coaching-service errors the API layer translates
    into specific HTTP responses."""


class ConversationNotFoundError(CoachingServiceError):
    pass


class ReadinessNotFoundError(CoachingServiceError):
    """Raised when coaching is requested before Phase 9's readiness
    verdict has been computed — coaching is grounded in the verdict and
    reasoning, so it requires them to already exist. This module never
    triggers `POST .../readiness` itself."""


class CoachingNotFoundError(CoachingServiceError):
    """Raised on `GET .../coaching` when no coaching session has been
    generated yet for an otherwise-valid, evaluated-and-assessed
    conversation."""


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
                joinedload(Conversation.coaching_session),
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
    return [
        CompetencyResult(
            competency_key=e.competency.key,
            display_name=e.competency.display_name,
            score=e.score,
            min_score=thresholds[e.competency.key],
        )
        for e in conversation.evaluations
        if e.competency.key in thresholds
    ]


def _build_prompt_competencies(conversation: Conversation, thresholds: dict[str, int]) -> list[dict]:
    ordered = sorted(conversation.evaluations, key=lambda e: MVP_COMPETENCY_KEYS.index(e.competency.key))
    return [
        {
            "competency_key": e.competency.key,
            "display_name": e.competency.display_name,
            "score": e.score,
            "min_score": thresholds[e.competency.key],
            "diagnosis": e.diagnosis,
            "impact": e.impact,
            "recommendation": e.recommendation,
            "evidence": [
                {"id": ev.id, "quote": ev.quote, "note": ev.note}
                for ev in sorted(e.evidence, key=lambda ev: ev.message.turn_index)
            ],
        }
        for e in ordered
    ]


def _deterministic_summary(priority: PriorityPick, verdict: str) -> str:
    """Used when the LLM is unavailable or its output never validates —
    a fixed, honest fallback built entirely from data already computed
    deterministically above, so a coaching session is never blocked on
    the LLM (same graceful-degradation posture as Phase 8's scoring)."""
    return (
        f"Readiness verdict: {verdict}. Priority focus: {priority.display_name}. {priority.reason} "
        "Review the diagnosis and recommendation for this competency below."
    )


def compute_and_persist_coaching(db: Session, conversation_id: str, provider: LLMProvider) -> CoachingSession:
    """Idempotent: returns the existing `coaching_sessions` row unchanged
    if one already exists, rather than regenerating (avoids duplicate
    rows and unnecessary repeat LLM calls, same posture as Phase 8's
    evaluation idempotency)."""
    conversation = _load_conversation_full(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    if conversation.coaching_session is not None:
        return conversation.coaching_session

    if conversation.readiness_result is None:
        raise ReadinessNotFoundError(conversation_id)

    thresholds = _thresholds_by_key(conversation)
    results = _build_competency_results(conversation)

    try:
        priority = pick_priority(results, MVP_COMPETENCY_KEYS)
    except PriorityNoCompetencyResultsError as exc:
        raise ReadinessNotFoundError(conversation_id) from exc

    readiness = conversation.readiness_result
    prompt_competencies = _build_prompt_competencies(conversation, thresholds)

    generation_result, _degraded = generate_coaching(
        provider,
        prompt_competencies,
        readiness.verdict,
        readiness.reasoning,
        priority.competency_key,
        priority.reason,
    )

    evaluated_keys = {e.competency.key for e in conversation.evaluations}
    valid_evidence_ids_by_competency = {
        e.competency.key: {ev.id for ev in e.evidence} for e in conversation.evaluations
    }

    if generation_result is None:
        summary = _deterministic_summary(priority, readiness.verdict)
        points: list[dict] = []
    else:
        verified = verify_coaching_points(
            generation_result.points, valid_evidence_ids_by_competency, evaluated_keys
        )
        summary = generation_result.summary
        points = [
            {"competency_key": p.competency_key, "evidence_id": p.evidence_id, "message": p.message}
            for p in verified
        ]

    coaching = CoachingSession(
        conversation_id=conversation.id,
        priority_competency_key=priority.competency_key,
        priority_reason=priority.reason,
        summary=summary,
        points=points,
    )
    db.add(coaching)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(coaching)
    return coaching


def get_coaching(db: Session, conversation_id: str) -> CoachingSession:
    conversation = _load_conversation_full(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)
    if conversation.coaching_session is None:
        raise CoachingNotFoundError(conversation_id)
    return conversation.coaching_session


def to_coaching_session_out(coaching: CoachingSession) -> CoachingSessionOut:
    return CoachingSessionOut(
        id=coaching.id,
        conversation_id=coaching.conversation_id,
        priority_competency_key=coaching.priority_competency_key,
        priority_reason=coaching.priority_reason,
        summary=coaching.summary,
        points=[CoachingPointOut(**p) for p in coaching.points],
        created_at=coaching.created_at,
    )
