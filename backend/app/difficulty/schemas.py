"""
API response schema for the difficulty module. Same reasoning as
readiness/schemas.py, coaching/schemas.py, drills/schemas.py: separate
from the ORM, structurally excludes hidden buyer state, system-prompt/
provider detail, and internal reasoning about anything other than the
difficulty decision itself — none of those fields exist here to begin
with, by construction (see decision.py, which has no LLM call to leak
from in the first place).
"""
from __future__ import annotations

from pydantic import BaseModel


class DifficultyRecommendationOut(BaseModel):
    conversation_id: str
    verdict: str
    current_difficulty: str
    recommended_difficulty: str
    direction: str
    reasoning: str
