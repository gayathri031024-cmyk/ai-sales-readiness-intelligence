"""
Root-cause-analysis orchestration (Phase 14).

Reads Phase 8's already-persisted `Evaluation` scores/diagnoses,
Phase 5's already-seeded `ScenarioCompetencyThreshold` rows, and the
static, Phase-14-seeded `SkillGraphEdge` rows; runs the pure
`find_related_weaknesses` function (no LLM, no network call, zero
cost — same posture as `readiness/`/`difficulty/`); returns the
result. Requires Phase 8's evaluation to already exist (this module
reads evaluation diagnoses directly, so there is nothing to analyze
without them) and never triggers it itself — the same "propose vs.
decide, never silently compute a prerequisite step" discipline every
module since `readiness/service.py` has followed. Does NOT require
Phase 9's readiness verdict — root-cause analysis is a function of
per-competency pass/fail, which evaluation + thresholds alone already
fully determine; requiring the verdict too would be an unnecessary
coupling to a fact this module never actually reads. See DECISIONS.md,
Phase 14.

Deliberately does NOT persist anything — same reasoning as
`difficulty/service.py`: a pure, free-to-recompute function of data
that is already durably persisted one layer down, so it is always
computed fresh rather than cached or snapshotted.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Conversation, Evaluation, Scenario, ScenarioCompetencyThreshold, SkillGraphEdge
from app.readiness.decision import CompetencyResult
from app.skill_graph.analysis import SkillGraphEdgeInfo, find_related_weaknesses
from app.skill_graph.schemas import CompetencyRootCauseOut, RelatedWeaknessOut, RootCauseAnalysisOut


class SkillGraphServiceError(Exception):
    """Base class for skill-graph-service errors the API layer
    translates into specific HTTP responses."""


class ConversationNotFoundError(SkillGraphServiceError):
    pass


class EvaluationNotFoundError(SkillGraphServiceError):
    """Raised when root-cause analysis is requested before the
    conversation has any Phase 8 evaluation — there is nothing to
    analyze yet. This module never triggers `POST .../evaluate`
    itself."""


def _load_conversation_full(db: Session, conversation_id: str) -> Conversation | None:
    return (
        db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                joinedload(Conversation.evaluations).joinedload(Evaluation.competency),
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


def _diagnoses_by_key(conversation: Conversation) -> dict[str, str]:
    return {e.competency.key: e.diagnosis for e in conversation.evaluations}


def _load_skill_graph_edges(db: Session) -> list[SkillGraphEdgeInfo]:
    edges = db.execute(
        select(SkillGraphEdge).options(
            joinedload(SkillGraphEdge.from_competency),
            joinedload(SkillGraphEdge.to_competency),
        )
    ).scalars().all()
    return [
        SkillGraphEdgeInfo(
            from_competency_key=edge.from_competency.key,
            to_competency_key=edge.to_competency.key,
        )
        for edge in edges
    ]


def compute_root_cause_analysis(db: Session, conversation_id: str) -> RootCauseAnalysisOut:
    """Stateless — always computed fresh from already-persisted data,
    never cached or written back. Two calls in a row against unchanged
    upstream data always return an identical result."""
    conversation = _load_conversation_full(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    if not conversation.evaluations:
        raise EvaluationNotFoundError(conversation_id)

    thresholds = _thresholds_by_key(conversation)
    results = _build_competency_results(conversation, thresholds)
    diagnoses = _diagnoses_by_key(conversation)
    edges = _load_skill_graph_edges(db)

    related_by_key = find_related_weaknesses(results, diagnoses, edges)

    display_names = {r.competency_key: r.display_name for r in results}
    root_causes = [
        CompetencyRootCauseOut(
            competency_key=key,
            display_name=display_names.get(key, key),
            related_weaknesses=[
                RelatedWeaknessOut(
                    competency_key=w.competency_key, display_name=w.display_name, reason=w.reason
                )
                for w in weaknesses
            ],
        )
        for key, weaknesses in related_by_key.items()
    ]

    return RootCauseAnalysisOut(conversation_id=conversation.id, root_causes=root_causes)
