"""
Difficulty-recommendation orchestration (Phase 12).

Reads Phase 8's already-persisted `Evaluation` scores, Phase 5's already-
seeded `ScenarioCompetencyThreshold` rows, and Phase 9's already-persisted
`ReadinessResult` verdict, runs the pure `recommend_difficulty` function
(no LLM, no network call, zero cost — same posture as `readiness/`), and
returns the recommendation. Never triggers Phase 9's readiness
computation itself, even lazily — the same "propose vs. decide, and
never silently compute a prerequisite step" discipline every module
since `readiness/service.py` has followed.

Deliberately does NOT persist anything. Unlike `ReadinessResult`,
`CoachingSession`, or `Drill`, a difficulty recommendation is not itself
a new fact requiring an audit trail — it is a pure, free-to-recompute
function of data that is already durably persisted one layer down
(the evaluation scores, thresholds, and readiness verdict this module
reads). Recomputing it on every request costs nothing and can never
drift from those already-authoritative sources. See DECISIONS.md,
Phase 12, for the full reasoning and the alternative considered.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Conversation, Evaluation, Scenario, ScenarioCompetencyThreshold
from app.difficulty.decision import (
    DifficultyRecommendation,
    NoCompetencyResultsError as DecisionNoCompetencyResultsError,
    UnknownDifficultyError,
    recommend_difficulty,
)
from app.difficulty.schemas import DifficultyRecommendationOut
from app.readiness.decision import CompetencyResult


class DifficultyServiceError(Exception):
    """Base class for difficulty-service errors the API layer translates
    into specific HTTP responses."""


class ConversationNotFoundError(DifficultyServiceError):
    pass


class ReadinessNotFoundError(DifficultyServiceError):
    """Raised when a difficulty recommendation is requested before the
    conversation has a computed Phase 9 readiness verdict — the
    recommendation is grounded in that verdict, so it requires it to
    already exist. This module never triggers `POST .../readiness`
    itself."""


class ScenarioDifficultyInvalidError(DifficultyServiceError):
    """Raised if the conversation's scenario has a `difficulty` value
    outside the known ladder (`easy`/`standard`/`hard`). Should never
    happen against the seeded MVP scenario, but surfaced as an explicit
    error rather than silently guessing a value — same "guard, don't
    fabricate" posture as `readiness/service.py::ThresholdMissingError`."""


def _load_conversation_full(db: Session, conversation_id: str) -> Conversation | None:
    return (
        db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                joinedload(Conversation.evaluations).joinedload(Evaluation.competency),
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


def _build_competency_results(conversation: Conversation, thresholds: dict[str, int]) -> list[CompetencyResult]:
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


def compute_difficulty_recommendation(db: Session, conversation_id: str) -> DifficultyRecommendationOut:
    """Stateless — always computed fresh from already-persisted data,
    never cached or written back (see module docstring). Two calls in a
    row against unchanged upstream data always return an identical
    result, since the underlying function is pure."""
    conversation = _load_conversation_full(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    if conversation.readiness_result is None:
        raise ReadinessNotFoundError(conversation_id)

    thresholds = _thresholds_by_key(conversation)
    results = _build_competency_results(conversation, thresholds)

    try:
        recommendation = recommend_difficulty(
            results,
            conversation.readiness_result.verdict,
            conversation.scenario.difficulty,
        )
    except DecisionNoCompetencyResultsError as exc:
        # Should never happen — a persisted `ReadinessResult` always
        # implies `decide_readiness` was called with a non-empty list
        # (Phase 9's own invariant). Guard anyway rather than crash.
        raise ReadinessNotFoundError(conversation_id) from exc
    except UnknownDifficultyError as exc:
        raise ScenarioDifficultyInvalidError(str(exc)) from exc

    return to_difficulty_recommendation_out(conversation.id, recommendation)


def to_difficulty_recommendation_out(
    conversation_id: str, recommendation: DifficultyRecommendation
) -> DifficultyRecommendationOut:
    return DifficultyRecommendationOut(
        conversation_id=conversation_id,
        verdict=recommendation.verdict,
        current_difficulty=recommendation.current_difficulty,
        recommended_difficulty=recommendation.recommended_difficulty,
        direction=recommendation.direction,
        reasoning=recommendation.reasoning,
    )
