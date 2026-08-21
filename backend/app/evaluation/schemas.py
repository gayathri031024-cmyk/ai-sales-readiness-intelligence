"""
API response schemas for the evaluation module.

Same reasoning as conversation/schemas.py and scenario/schemas.py:
deliberately separate from the ORM models so a DB column can change
without silently changing the wire format.

CRITICAL: exactly like conversation/schemas.py's rule for hidden buyer
state, this file never references trust/patience/budget_sensitivity/
interest, and never references any raw LLM prompt, system prompt,
provider name/model, or internal reasoning/rationale text — per this
phase's public-API requirement. `EvidenceOut` exposes only what a rep
or reviewer should see: the quote, an optional human-readable note, and
where in the transcript it came from.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    turn_index: int
    quote: str
    note: str | None


class EvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competency_key: str
    display_name: str
    score: int
    diagnosis: str
    impact: str
    recommendation: str
    created_at: datetime
    evidence: list[EvidenceOut]


class ConversationEvaluationOut(BaseModel):
    """The full Phase 8 result for one conversation: one entry per MVP
    competency. Deliberately does NOT include a readiness verdict —
    that's Phase 9 scope (see PHASE BOUNDARY)."""

    conversation_id: str
    evaluations: list[EvaluationOut]
