"""
API response schemas for the coaching module. Same reasoning as
evaluation/schemas.py and readiness/schemas.py: separate from the ORM,
and structurally excludes hidden buyer state, system-prompt/provider
detail, and internal reasoning — none of those fields exist here to
begin with, by construction (see generation.py/verification.py).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CoachingPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    competency_key: str
    evidence_id: str | None
    message: str


class CoachingSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    priority_competency_key: str
    priority_reason: str
    summary: str
    points: list[CoachingPointOut]
    created_at: datetime
