"""
API response/request schemas for the conversation module.

Deliberately separate from the ORM models (db/models.py), same reasoning
as scenario/schemas.py: this defines the *public* HTTP contract, so a DB
column can change without silently changing the wire format.

CRITICAL: `current_buyer_state` / `BuyerStateHistory` are never referenced
anywhere in this file. That is not an oversight to double-check later —
it is the enforced boundary from ARCHITECTURE.md §6 ("the API response
schema for any message/turn endpoint explicitly excludes state fields at
the serializer level"). Do not add trust/patience/budget_sensitivity/
interest to any schema below.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StartConversationIn(BaseModel):
    scenario_id: str


class SendTurnIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    """Public transcript line. `classified_intent` is intentionally
    omitted — it's an internal AI-classification detail (per
    ARCHITECTURE.md §4A / the Phase 7 spec's hidden-state-protection
    requirement), not public product behavior."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    turn_index: int
    sender: str
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    """Public conversation state. No hidden buyer state, ever."""

    id: str
    scenario_id: str
    status: str
    end_reason: str | None
    turn_count: int
    max_turns: int
    started_at: datetime
    completed_at: datetime | None
    messages: list[MessageOut]
