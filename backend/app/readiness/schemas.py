"""
API response schemas for the readiness module.

Same "separate from the ORM" reasoning as evaluation/schemas.py and
conversation/schemas.py. `EvaluationWithThresholdOut` extends Phase 8's
`EvaluationOut` shape with the one field Phase 8 deliberately left out —
`required_min_score` — since Phase 8's own PHASE BOUNDARY excluded any
readiness-threshold comparison (see DECISIONS.md, Phase 8's endpoint-
naming decision). `evidence` reuses Phase 8's `EvidenceOut` unchanged —
no reason to redefine it.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.evaluation.schemas import EvidenceOut


class ReadinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    verdict: str
    reasoning: str
    computed_at: datetime


class EvaluationWithThresholdOut(BaseModel):
    id: str
    competency_key: str
    display_name: str
    score: int
    required_min_score: int
    diagnosis: str
    impact: str
    recommendation: str
    created_at: datetime
    evidence: list[EvidenceOut]


class ConversationResultOut(BaseModel):
    """The complete Result-screen shape ARCHITECTURE.md §2 always intended
    — Phase 8's evidence-based evaluations, each now carrying its scenario
    threshold, alongside Phase 9's deterministic readiness verdict."""

    conversation_id: str
    verdict: str
    reasoning: str
    computed_at: datetime
    evaluations: list[EvaluationWithThresholdOut]
