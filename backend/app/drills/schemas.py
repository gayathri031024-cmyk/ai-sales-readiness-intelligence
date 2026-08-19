"""
API response schemas for the drills module. Same reasoning as
evaluation/schemas.py, readiness/schemas.py, coaching/schemas.py:
separate from the ORM, structurally excludes hidden buyer state,
system-prompt/provider detail, and internal reasoning — none of those
fields exist here to begin with, by construction (see generation.py,
which has no LLM call to leak from in the first place).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DrillFocusPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    competency_key: str
    evidence_id: str | None
    message: str


class DrillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    competency_key: str
    display_name: str
    practice_scenario_id: str
    title: str
    focus_reason: str
    instructions: str
    focus_points: list[DrillFocusPointOut]
    created_at: datetime
