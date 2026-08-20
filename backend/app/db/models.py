"""
ORM models — mirrors DATA_MODEL.md exactly. MVP scope only.

Deliberately absent: organizations, products catalog, reassessments,
skill_graph_edges, manager_rollups. See DATA_MODEL.md §3 "Explicitly
Deferred". (coaching_sessions, drills, and knowledge_documents/
knowledge_chunks were built in Phases 10, 11, and 13 respectively —
this comment previously listed them as absent after they'd already
shipped; corrected here.)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")


class BuyerPersona(Base):
    __tablename__ = "buyer_personas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    base_state: Mapped[dict] = mapped_column(JSON)  # trust/patience/budget_sensitivity/interest
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    scenarios: Mapped[list["Scenario"]] = relationship(back_populates="buyer_persona")


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255))
    buyer_persona_id: Mapped[str] = mapped_column(ForeignKey("buyer_personas.id"))
    product_context: Mapped[str] = mapped_column(Text)
    known_objection: Mapped[str] = mapped_column(String(255))
    difficulty: Mapped[str] = mapped_column(String(50), default="standard")
    max_turns: Mapped[int] = mapped_column(Integer, default=20)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    buyer_persona: Mapped["BuyerPersona"] = relationship(back_populates="scenarios")
    thresholds: Mapped[list["ScenarioCompetencyThreshold"]] = relationship(back_populates="scenario")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="scenario")


class Competency(Base):
    __tablename__ = "competencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(100), unique=True)  # discovery / objection_handling / closing
    display_name: Mapped[str] = mapped_column(String(255))


class ScenarioCompetencyThreshold(Base):
    __tablename__ = "scenario_competency_thresholds"

    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), primary_key=True)
    competency_id: Mapped[str] = mapped_column(ForeignKey("competencies.id"), primary_key=True)
    min_score: Mapped[int] = mapped_column(Integer)

    scenario: Mapped["Scenario"] = relationship(back_populates="thresholds")
    competency: Mapped["Competency"] = relationship()


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"))
    status: Mapped[str] = mapped_column(String(50), default="in_progress")
    # NEVER serialize this field in any API response schema — see ARCHITECTURE.md §6.
    current_buyer_state: Mapped[dict] = mapped_column(JSON)
    end_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="conversations")
    scenario: Mapped["Scenario"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", order_by="Message.turn_index")
    state_history: Mapped[list["BuyerStateHistory"]] = relationship(back_populates="conversation")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="conversation")
    readiness_result: Mapped["ReadinessResult"] = relationship(back_populates="conversation", uselist=False)
    coaching_session: Mapped["CoachingSession"] = relationship(back_populates="conversation", uselist=False)
    drill: Mapped["Drill"] = relationship(back_populates="conversation", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    turn_index: Mapped[int] = mapped_column(Integer)
    sender: Mapped[str] = mapped_column(String(10))  # "rep" | "buyer"
    content: Mapped[str] = mapped_column(Text)
    classified_intent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class BuyerStateHistory(Base):
    """Append-only debug/audit log — not user-facing. Exists to test the Phase 0
    assumptions around state leakage and state-evolution sanity (see DECISIONS.md)."""

    __tablename__ = "buyer_state_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    turn_index: Mapped[int] = mapped_column(Integer)
    state: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="state_history")


class Evaluation(Base):
    """One row per competency per conversation — keeps evidence cleanly scoped."""

    __tablename__ = "evaluations"
    __table_args__ = (UniqueConstraint("conversation_id", "competency_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    competency_id: Mapped[str] = mapped_column(ForeignKey("competencies.id"))
    score: Mapped[int] = mapped_column(Integer)
    diagnosis: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="evaluations")
    competency: Mapped["Competency"] = relationship()
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="evaluation")


class Evidence(Base):
    """Tied to an actual Message row — an evaluator can never cite a quote
    that wasn't actually said. See DECISIONS.md."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluations.id"))
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"))
    quote: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    evaluation: Mapped["Evaluation"] = relationship(back_populates="evidence")
    message: Mapped["Message"] = relationship()


class ReadinessResult(Base):
    __tablename__ = "readiness_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), unique=True)
    verdict: Mapped[str] = mapped_column(String(20))  # READY | NOT_READY | AT_RISK
    reasoning: Mapped[str] = mapped_column(Text)
    thresholds_snapshot: Mapped[dict] = mapped_column(JSON)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="readiness_result")


class CoachingSession(Base):
    """Phase 10 — one per conversation (idempotent, like ReadinessResult).
    Synthesizes Phase 8's per-competency evidence/diagnosis and Phase 9's
    readiness verdict into a prioritized coaching narrative. `points` is a
    JSON list (same established pattern as `thresholds_snapshot` above)
    of already-grounded {competency_key, evidence_id, message} entries —
    see app/coaching/verification.py for how "already-grounded" is
    enforced deterministically before persistence."""

    __tablename__ = "coaching_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), unique=True)
    priority_competency_key: Mapped[str] = mapped_column(String(100))
    priority_reason: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    points: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="coaching_session")


class Drill(Base):
    """Phase 11 — one per conversation (idempotent, same posture as
    ReadinessResult/CoachingSession). A "targeted drill": a deterministic
    reassembly of Phase 10's already-generated coaching (priority pick +
    grounded points) and Phase 8's evaluation diagnosis/recommendation
    for that one priority competency, into a focused practice assignment.

    No new facts are ever introduced here — `app/drills/generation.py`
    makes zero LLM calls (see DECISIONS.md, Phase 11); every field is
    built entirely from already-verified upstream text.

    `practice_scenario_id` points at the scenario to practice again —
    in the MVP this is always the origin conversation's own scenario,
    since no multi-scenario library exists yet (see DECISIONS.md,
    Phase 11, for why this phase does not invent one). `focus_points` is
    a JSON list (same established pattern as `CoachingSession.points`)
    of the subset of that session's already-grounded coaching points
    whose `competency_key` matches this drill's priority competency."""

    __tablename__ = "drills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), unique=True)
    competency_id: Mapped[str] = mapped_column(ForeignKey("competencies.id"))
    practice_scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"))
    title: Mapped[str] = mapped_column(String(255))
    focus_reason: Mapped[str] = mapped_column(Text)
    instructions: Mapped[str] = mapped_column(Text)
    focus_points: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="drill")
    competency: Mapped["Competency"] = relationship()
    practice_scenario: Mapped["Scenario"] = relationship()


class KnowledgeDocument(Base):
    """Phase 13 — one uploaded product/company knowledge source
    (playbook, FAQ, battle card, pricing sheet, spec doc — see
    MASTER_PROMPT.md "RAG / PRODUCT KNOWLEDGE"). `content` keeps the
    full original text so chunking can be re-run deterministically if
    the chunking strategy ever changes, without re-uploading."""

    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunk.chunk_index",
    )


class KnowledgeChunk(Base):
    """One deterministically-chunked span of a KnowledgeDocument, plus
    its embedding vector. `embedding` is a plain JSON float array, not
    a pgvector column — per DECISIONS.md (Phase 13), similarity search
    runs in-process (pure Python cosine similarity, see
    app/knowledge/retrieval.py) at MVP scale; pgvector is deferred to
    Phase 21 deployment when a real Postgres target and larger corpus
    justify it (see ARCHITECTURE.md §10, DATA_MODEL.md §3)."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")
