"""
Buyer hidden-state schema.

Exactly the 4 dimensions established in PHASE_0_PRODUCT_STRATEGY.md §7
("3-4 dimensions, not 7+") and DATA_MODEL.md's `buyer_personas.base_state`
/ `conversations.current_buyer_state` columns: trust, patience,
budget_sensitivity, interest. Do not add a 5th dimension here — that's
exactly the scope creep Phase 0 and this Phase 6 prompt both explicitly
rule out.

This schema is intentionally decoupled from the ORM (`db/models.py`
stores it as a plain JSON column) so it can be validated and unit-tested
without a database. `BuyerState.model_dump()` is what gets persisted
into `current_buyer_state` / `buyer_state_history.state`.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

STATE_MIN = 0
STATE_MAX = 100


def clamp(value: int) -> int:
    return max(STATE_MIN, min(STATE_MAX, value))


class BuyerState(BaseModel):
    """All four dimensions are bounded [0, 100]. Values are clamped, not
    rejected, on construction — a rule-table delta pushing a dimension
    past a boundary is an expected, routine occurrence (e.g. trust
    already at 98, +5 delta), not a data error."""

    trust: int = Field(ge=STATE_MIN, le=STATE_MAX)
    patience: int = Field(ge=STATE_MIN, le=STATE_MAX)
    budget_sensitivity: int = Field(ge=STATE_MIN, le=STATE_MAX)
    interest: int = Field(ge=STATE_MIN, le=STATE_MAX)

    @field_validator("trust", "patience", "budget_sensitivity", "interest", mode="before")
    @classmethod
    def _clamp(cls, v: int) -> int:
        return clamp(int(v))

    def apply_deltas(self, deltas: "StateDelta") -> "BuyerState":
        """Pure — returns a new BuyerState, does not mutate self. This is
        the only way state should ever change; see rules.py."""
        return BuyerState(
            trust=self.trust + deltas.trust,
            patience=self.patience + deltas.patience,
            budget_sensitivity=self.budget_sensitivity + deltas.budget_sensitivity,
            interest=self.interest + deltas.interest,
        )


class StateDelta(BaseModel):
    """Signed deltas applied to a BuyerState. Unbounded here on purpose —
    clamping happens once, at the BuyerState boundary, not per-delta, so
    rule-table entries stay simple plain integers."""

    trust: int = 0
    patience: int = 0
    budget_sensitivity: int = 0
    interest: int = 0
