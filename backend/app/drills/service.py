"""
Drill orchestration (Phase 11).

Reads Phase 8's already-persisted `Evaluation` and Phase 10's
already-persisted `CoachingSession`, runs the pure `generate_drill`
function (no LLM, no DB), then persists one `Drill` row per
conversation. Never triggers coaching (or readiness, or evaluation)
itself — all three must already exist, the same "propose vs. decide,
and never silently compute a prerequisite step" discipline as
`readiness/service.py` and `coaching/service.py` before it.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import CoachingSession, Competency, Conversation, Drill, Evaluation
from app.drills.generation import generate_drill
from app.drills.schemas import DrillFocusPointOut, DrillOut


class DrillServiceError(Exception):
    """Base class for drill-service errors the API layer translates into
    specific HTTP responses."""


class ConversationNotFoundError(DrillServiceError):
    pass


class CoachingNotFoundError(DrillServiceError):
    """Raised when a drill is requested before Phase 10's coaching
    session has been generated — a drill is built entirely from
    already-verified coaching output, so it requires that output to
    already exist. This module never triggers `POST .../coaching`
    itself."""


class DrillNotFoundError(DrillServiceError):
    """Raised on `GET .../drill` when no drill has been generated yet
    for an otherwise-valid, coached conversation."""


def _load_conversation_full(db: Session, conversation_id: str) -> Conversation | None:
    return (
        db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                joinedload(Conversation.evaluations).joinedload(Evaluation.competency),
                joinedload(Conversation.coaching_session),
                joinedload(Conversation.drill).joinedload(Drill.competency),
                joinedload(Conversation.drill).joinedload(Drill.practice_scenario),
            )
        )
        .unique()
        .scalar_one_or_none()
    )


def _competency_by_key(db: Session, key: str) -> Competency | None:
    return db.execute(select(Competency).where(Competency.key == key)).scalar_one_or_none()


def compute_and_persist_drill(db: Session, conversation_id: str) -> Drill:
    """Idempotent: returns the existing `drills` row unchanged if one
    already exists, rather than regenerating (avoids duplicate rows —
    same posture as Phase 9/10's idempotency, though here there's no LLM
    cost to save, only consistency: a drill a rep already started
    reading shouldn't silently change under them)."""
    conversation = _load_conversation_full(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    if conversation.drill is not None:
        return conversation.drill

    if conversation.coaching_session is None:
        raise CoachingNotFoundError(conversation_id)

    coaching = conversation.coaching_session
    priority_key = coaching.priority_competency_key

    evaluation = next((e for e in conversation.evaluations if e.competency.key == priority_key), None)
    # Should never happen — coaching's priority pick always comes from an
    # already-evaluated competency (Phase 10's `pick_priority` reads
    # straight from `conversation.evaluations`). Guard anyway rather than
    # crash on a KeyError if the data is ever in an unexpected state.
    diagnosis = evaluation.diagnosis if evaluation else "No diagnosis was recorded for this competency."
    recommendation = evaluation.recommendation if evaluation else "Review this competency in your next attempt."
    priority_display_name = evaluation.competency.display_name if evaluation else priority_key.replace("_", " ").title()

    competency = _competency_by_key(db, priority_key)
    if competency is None:
        # Same "should never happen, guard don't crash" posture as
        # evaluation/service.py's identical check.
        raise CoachingNotFoundError(conversation_id)

    generated = generate_drill(
        priority_competency_key=priority_key,
        priority_display_name=priority_display_name,
        priority_reason=coaching.priority_reason,
        diagnosis=diagnosis,
        recommendation=recommendation,
        coaching_points=coaching.points,
    )

    drill = Drill(
        conversation_id=conversation.id,
        competency_id=competency.id,
        practice_scenario_id=conversation.scenario_id,
        title=generated.title,
        focus_reason=generated.focus_reason,
        instructions=generated.instructions,
        focus_points=[
            {"competency_key": p.competency_key, "evidence_id": p.evidence_id, "message": p.message}
            for p in generated.focus_points
        ],
    )
    db.add(drill)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(drill)
    return drill


def get_drill(db: Session, conversation_id: str) -> Drill:
    conversation = _load_conversation_full(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)
    if conversation.drill is None:
        raise DrillNotFoundError(conversation_id)
    return conversation.drill


def to_drill_out(drill: Drill) -> DrillOut:
    return DrillOut(
        id=drill.id,
        conversation_id=drill.conversation_id,
        competency_key=drill.competency.key,
        display_name=drill.competency.display_name,
        practice_scenario_id=drill.practice_scenario_id,
        title=drill.title,
        focus_reason=drill.focus_reason,
        instructions=drill.instructions,
        focus_points=[DrillFocusPointOut(**p) for p in drill.focus_points],
        created_at=drill.created_at,
    )
