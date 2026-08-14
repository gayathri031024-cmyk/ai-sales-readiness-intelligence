"""
ORM models — mirrors DATA_MODEL.md exactly. MVP scope only.

Deliberately absent: organizations, products catalog, knowledge_documents
(RAG), coaching_sessions, drills, reassessments, skill_graph_edges,
manager_rollups. See DATA_MODEL.md §3 "Explicitly Deferred".
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
