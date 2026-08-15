"""
Conversation persistence + multi-turn orchestration.

Owns exactly what ARCHITECTURE.md §3 assigns to `conversation/`: turn
persistence, turn-taking, and end-condition logic. The buyer's actual
turn logic (classify -> deterministic state update -> reply) remains
entirely owned by `buyer/service.run_buyer_turn` — this module loads
persisted state, calls that single entrypoint once per turn, and
persists the result. No second state-update system is introduced here.

Core flow per DECISIONS.md / the Phase 7 spec:

    load persisted conversation + hidden state
            |
    app.buyer.service.run_buyer_turn()
            |
    persist updated hidden state + both messages + turn count
            |
    evaluate end conditions
            |
    return public conversation state
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.ai.provider import LLMProvider
from app.buyer.service import run_buyer_turn
from app.buyer.state import BuyerState
from app.conversation.schemas import ConversationOut, MessageOut
from app.db.models import BuyerStateHistory, Conversation, Message, Scenario, User

_DEFAULT_USER_EMAIL = "dev@local.test"

# Conversation.status values — deliberately just the two DATA_MODEL.md
# already establishes (`in_progress` / `completed`). No third "failed"
# status is invented; failure is distinguished via `end_reason` instead
# (see _END_REASON_* below), per this phase's "don't invent a new status
# vocabulary" instruction.
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"

END_REASON_TURN_LIMIT = "turn_limit"
END_REASON_PATIENCE_EXHAUSTED = "patience_exhausted"
END_REASON_EXPLICIT_CLOSE = "explicit_close"

# Buyer state floor (see app/buyer/state.py STATE_MIN) — a buyer whose
# patience has been driven all the way to the clamp floor has, by
# construction, no patience left. Using the schema's own boundary value
# rather than an arbitrary new threshold keeps this end condition tied to
# the Phase 6 state model rather than inventing a second scoring system.
_PATIENCE_EXHAUSTED_THRESHOLD = 0


class ConversationServiceError(Exception):
    """Base class for conversation-service errors the API layer translates
    into specific HTTP responses. Never carries internal details in a form
    that would leak prompts, stack traces, or hidden state if serialized."""


class ScenarioNotFoundError(ConversationServiceError):
    pass


class ConversationNotFoundError(ConversationServiceError):
    pass


class ConversationNotActiveError(ConversationServiceError):
    """Raised when a turn is submitted against a conversation that has
    already reached a terminal status. Per the Phase 7 spec: once
    terminal, reject additional turns, never mutate state, never append
    messages."""


def get_or_create_default_user(db: Session) -> User:
    """MVP is single-user (per DATA_MODEL.md §users and ARCHITECTURE.md §8
    — multi-user auth is explicitly out of scope). Every conversation is
    still owned by a real `user_id` FK so multi-user support later is a
    data change, not a schema migration. Idempotent, same pattern as
    `scenario.service.seed_mvp_scenario`."""
    existing = db.execute(select(User).where(User.email == _DEFAULT_USER_EMAIL)).scalar_one_or_none()
    if existing is not None:
        return existing

    user = User(email=_DEFAULT_USER_EMAIL)
    db.add(user)
    db.flush()
    return user


def _load_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            joinedload(Conversation.scenario).joinedload(Scenario.buyer_persona),
            joinedload(Conversation.messages),
        )
    ).unique().scalar_one_or_none()


def to_conversation_out(conversation: Conversation) -> ConversationOut:
    """The single place that turns an ORM `Conversation` into the public
    API shape. `current_buyer_state` is a column on the ORM object right
    next to everything read here — it is never touched in this function,
    which is what keeps hidden state out of every response that flows
    through this helper."""
    turn_count = sum(1 for m in conversation.messages if m.sender == "rep")
    messages = sorted(conversation.messages, key=lambda m: m.turn_index)
    return ConversationOut(
        id=conversation.id,
        scenario_id=conversation.scenario_id,
        status=conversation.status,
        end_reason=conversation.end_reason,
        turn_count=turn_count,
        max_turns=conversation.scenario.max_turns,
        started_at=conversation.started_at,
        completed_at=conversation.completed_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


def start_conversation(db: Session, scenario_id: str) -> Conversation:
    """Creates a new conversation, initializes hidden buyer state from the
    scenario's persona `base_state`, and persists it. No opening buyer
    message is generated here — the rep speaks first (see DECISIONS.md);
    Phase 6's buyer engine always classifies a rep message before it
    replies, and inventing a second, ungated reply path just to produce
    a scripted opening line would be exactly the kind of Phase 6
    redesign this phase's PHASE BOUNDARY rules out."""
    scenario = db.execute(
        select(Scenario)
        .where(Scenario.id == scenario_id)
        .options(joinedload(Scenario.buyer_persona))
    ).unique().scalar_one_or_none()

    if scenario is None:
        raise ScenarioNotFoundError(scenario_id)

    user = get_or_create_default_user(db)

    conversation = Conversation(
        user_id=user.id,
        scenario_id=scenario.id,
        status=STATUS_IN_PROGRESS,
        current_buyer_state=dict(scenario.buyer_persona.base_state),
        end_reason=None,
    )
    db.add(conversation)
    db.commit()

    return _load_conversation(db, conversation.id)


def get_conversation(db: Session, conversation_id: str) -> Conversation:
    conversation = _load_conversation(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)
    return conversation


def _next_turn_indices(conversation: Conversation) -> tuple[int, int]:
    """Sequential message ordering (1-based), independent of rep/buyer
    turn counting — mirrors DATA_MODEL.md's `messages.turn_index` ("just
    ordering"). Returns (rep_message_turn_index, buyer_message_turn_index)."""
    last = max((m.turn_index for m in conversation.messages), default=0)
    return last + 1, last + 2


def submit_turn(db: Session, conversation_id: str, *, rep_message: str, provider: LLMProvider) -> Conversation:
    """Runs exactly one multi-turn exchange:

        load persisted conversation + hidden state
                |
        run_buyer_turn()  (Phase 6, unchanged)
                |
        persist updated hidden state, both messages, turn count
                |
        evaluate end conditions
                |
        return the conversation (public serialization happens one layer up)

    The next call to this function for the same conversation reads
    whatever `current_buyer_state` this call just persisted — that's the
    entire multi-turn persistence guarantee this phase exists to build.
    """
    conversation = _load_conversation(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    if conversation.status != STATUS_IN_PROGRESS:
        raise ConversationNotActiveError(conversation_id)

    scenario = conversation.scenario
    persona = scenario.buyer_persona

    current_state = BuyerState(**conversation.current_buyer_state)
    turn_number = sum(1 for m in conversation.messages if m.sender == "rep") + 1

    try:
        result = run_buyer_turn(
            provider,
            rep_message=rep_message,
            current_state=current_state,
            persona_name=persona.name,
            persona_description=persona.description,
            product_context=scenario.product_context,
            known_objection=scenario.known_objection,
            turn_index=turn_number - 1,
        )

        rep_turn_index, buyer_turn_index = _next_turn_indices(conversation)

        db.add(
            Message(
                conversation_id=conversation.id,
                turn_index=rep_turn_index,
                sender="rep",
                content=rep_message,
                classified_intent=result.classified_behavior.value,
            )
        )
        db.add(
            Message(
                conversation_id=conversation.id,
                turn_index=buyer_turn_index,
                sender="buyer",
                content=result.buyer_reply,
            )
        )
        db.add(
            BuyerStateHistory(
                conversation_id=conversation.id,
                turn_index=turn_number,
                state=result.new_state.model_dump(),
            )
        )

        conversation.current_buyer_state = result.new_state.model_dump()

        if turn_number >= scenario.max_turns:
            conversation.status = STATUS_COMPLETED
            conversation.end_reason = END_REASON_TURN_LIMIT
            conversation.completed_at = datetime.now(timezone.utc)
        elif result.new_state.patience <= _PATIENCE_EXHAUSTED_THRESHOLD:
            conversation.status = STATUS_COMPLETED
            conversation.end_reason = END_REASON_PATIENCE_EXHAUSTED
            conversation.completed_at = datetime.now(timezone.utc)

        db.commit()
    except Exception:
        # A successful turn must persist message + buyer response +
        # updated state + turn number consistently, or not at all — see
        # this phase's IDEMPOTENCY / DATA SAFETY section. run_buyer_turn
        # itself never raises for LLM-related failures (it degrades), so
        # anything reaching here is unexpected (e.g. a DB error) and must
        # not leave a half-written turn behind.
        db.rollback()
        raise

    return _load_conversation(db, conversation.id)


def close_conversation(db: Session, conversation_id: str) -> Conversation:
    """Explicit-close end condition (the frontend's "End conversation and
    see evaluation" action). Idempotent: closing an already-terminal
    conversation is a no-op, not an error — unlike `submit_turn`, closing
    is not a mutating action that could double-charge an LLM call or
    double-apply a state delta, so there's nothing unsafe about a repeat
    call."""
    conversation = _load_conversation(db, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    if conversation.status == STATUS_IN_PROGRESS:
        conversation.status = STATUS_COMPLETED
        conversation.end_reason = END_REASON_EXPLICIT_CLOSE
        conversation.completed_at = datetime.now(timezone.utc)
        db.commit()

    return _load_conversation(db, conversation.id)
