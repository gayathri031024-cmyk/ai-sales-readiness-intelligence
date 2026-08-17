"""
Evaluation pipeline orchestration (ARCHITECTURE.md §4B):

    conversation transcript
            |
    extract_evidence()        (evaluation/extraction.py — LLM, structured)
            |
    verify_evidence()         (evaluation/verification.py — deterministic)
            |
    score_competency() x3     (evaluation/scoring.py — LLM-assisted or
                                deterministic, per competency)
            |
    persist Evaluation + Evidence rows (this file)
            |
    return public shape (this file's `to_conversation_evaluation_out`)

Mirrors conversation/service.py's existing shape: a plain sequential
pipeline (not LangGraph, per DECISIONS.md Phase 1 — evaluation has no
looping/branching need), one DB transaction per full evaluation run,
rollback on any unexpected failure so a half-written evaluation is never
left behind.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.ai.provider import LLMProvider
from app.db.models import Competency, Conversation, Evaluation, Evidence, Message
from app.evaluation.extraction import MVP_COMPETENCY_KEYS, CompetencyKey, extract_evidence
from app.evaluation.schemas import ConversationEvaluationOut, EvaluationOut, EvidenceOut
from app.evaluation.scoring import score_competency
from app.evaluation.verification import TranscriptMessage, VerifiedEvidence, verify_evidence

# Conversation.status this pipeline requires before it will run — evaluation
# is a post-conversation step (ARCHITECTURE.md §5 data flow), not something
# that can run against an in-progress conversation with more turns to come.
_REQUIRED_STATUS = "completed"


class EvaluationServiceError(Exception):
    """Base class for evaluation-service errors the API layer translates
    into specific HTTP responses. Never carries internal details in a form
    that would leak prompts, transcripts, or hidden state if serialized."""


class ConversationNotFoundError(EvaluationServiceError):
    pass


class ConversationNotCompletedError(EvaluationServiceError):
    """Raised when evaluation is requested before the conversation has
    reached a terminal status. Evaluation is deliberately post-conversation
    only — evaluating a still-active conversation would score an
    incomplete performance."""


class EvaluationNotFoundError(EvaluationServiceError):
    """Raised on GET when no evaluation has been run yet for this
    (existing, valid) conversation."""


def _load_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(joinedload(Conversation.messages))
    ).unique().scalar_one_or_none()


def _load_competencies_by_key(db: Session) -> dict[CompetencyKey, Competency]:
    """MVP competencies are seeded once by `scenario.seed_mvp_scenario`
    (Phase 5) — this module reuses those rows rather than creating its
    own, per this phase's "reuse existing architecture" requirement."""
    rows = db.execute(
        select(Competency).where(Competency.key.in_(MVP_COMPETENCY_KEYS))
    ).scalars().all()
    return {row.key: row for row in rows}


def _load_existing_evaluations(db: Session, conversation_id: str) -> list[Evaluation]:
    return db.execute(
        select(Evaluation)
        .where(Evaluation.conversation_id == conversation_id)
        .options(
            joinedload(Evaluation.competency),
            joinedload(Evaluation.evidence).joinedload(Evidence.message),
        )
    ).unique().scalars().all()


def to_evaluation_out(evaluation: Evaluation) -> EvaluationOut:
    return EvaluationOut(
        id=evaluation.id,
        competency_key=evaluation.competency.key,
        display_name=evaluation.competency.display_name,
        score=evaluation.score,
        diagnosis=evaluation.diagnosis,
        impact=evaluation.impact,
        recommendation=evaluation.recommendation,
        created_at=evaluation.created_at,
        evidence=[
            EvidenceOut(
                id=e.id,
                message_id=e.message_id,
                turn_index=e.message.turn_index,
                quote=e.quote,
                note=e.note,
            )
            for e in sorted(evaluation.evidence, key=lambda e: e.message.turn_index)
        ],
    )


def to_conversation_evaluation_out(conversation_id: str, evaluations: list[Evaluation]) -> ConversationEvaluationOut:
    ordered = sorted(evaluations, key=lambda e: MVP_COMPETENCY_KEYS.index(e.competency.key))
    return ConversationEvaluationOut(
        conversation_id=conversation_id,
        evaluations=[to_evaluation_out(e) for e in ordered],
    )


def evaluate_conversation(db: Session, conversation_id: str, provider: LLMProvider) -> list[Evaluation]:
    """Runs the full pipeline and persists the result. Idempotent: if this
    conversation already has evaluation rows (from a prior run), returns
    them unchanged rather than re-extracting/re-scoring — avoids duplicate
    rows (the `(conversation_id, competency_id)` unique constraint would
    reject a re-insert anyway) and avoids unnecessary repeat LLM calls."""
    conversation = _load_conversation(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    if conversation.status != _REQUIRED_STATUS:
        raise ConversationNotCompletedError(conversation_id)

    existing = _load_existing_evaluations(db, conversation_id)
    if existing:
        return existing

    messages_sorted = sorted(conversation.messages, key=lambda m: m.turn_index)
    transcript_tuples = [(m.turn_index, m.sender, m.content) for m in messages_sorted]
    transcript_lookup = [
        TranscriptMessage(id=m.id, turn_index=m.turn_index, sender=m.sender, content=m.content)
        for m in messages_sorted
    ]

    candidates, _extraction_degraded = extract_evidence(provider, transcript_tuples)
    verified = verify_evidence(candidates, transcript_lookup)

    evidence_by_competency: dict[CompetencyKey, list[VerifiedEvidence]] = {key: [] for key in MVP_COMPETENCY_KEYS}
    for item in verified:
        evidence_by_competency[item.competency_key].append(item)

    competencies_by_key = _load_competencies_by_key(db)

    try:
        persisted: list[Evaluation] = []
        for key in MVP_COMPETENCY_KEYS:
            competency = competencies_by_key.get(key)
            if competency is None:
                # Should never happen — competencies are seeded alongside
                # the MVP scenario (scenario/service.py). Skip rather than
                # crash the whole evaluation if the DB is ever in a state
                # this phase didn't create.
                continue

            evidence_items = evidence_by_competency[key]
            result, _scoring_degraded = score_competency(provider, key, evidence_items)

            evaluation = Evaluation(
                conversation_id=conversation.id,
                competency_id=competency.id,
                score=result.score,
                diagnosis=result.diagnosis,
                impact=result.impact,
                recommendation=result.recommendation,
            )
            db.add(evaluation)
            db.flush()  # need evaluation.id before creating Evidence rows

            for item in evidence_items:
                db.add(
                    Evidence(
                        evaluation_id=evaluation.id,
                        message_id=item.message_id,
                        quote=item.quote,
                        note=item.note,
                    )
                )

            persisted.append(evaluation)

        db.commit()
    except Exception:
        # A complete evaluation run must persist all three competency
        # evaluations (plus their evidence) consistently, or none at all —
        # same "all or nothing per operation" discipline as
        # conversation/service.py's submit_turn.
        db.rollback()
        raise

    return _load_existing_evaluations(db, conversation_id)


def get_evaluation(db: Session, conversation_id: str) -> list[Evaluation]:
    conversation = _load_conversation(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    evaluations = _load_existing_evaluations(db, conversation_id)
    if not evaluations:
        raise EvaluationNotFoundError(conversation_id)

    return evaluations
