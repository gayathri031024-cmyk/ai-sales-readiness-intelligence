"""
API schemas for the skill-graph/root-cause module. Same reasoning as
every other module's schemas.py: separate from the ORM, structurally
excludes anything internal.
"""
from __future__ import annotations

from pydantic import BaseModel


class RelatedWeaknessOut(BaseModel):
    competency_key: str
    display_name: str
    reason: str


class CompetencyRootCauseOut(BaseModel):
    competency_key: str
    display_name: str
    related_weaknesses: list[RelatedWeaknessOut]


class RootCauseAnalysisOut(BaseModel):
    conversation_id: str
    root_causes: list[CompetencyRootCauseOut]
