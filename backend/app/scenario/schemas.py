"""
API response schemas for the scenario module.

Deliberately separate from the ORM models (db/models.py): these define the
*public* shape returned over HTTP, so a DB column can be added or renamed
without silently changing the API contract. Mirrors the frontend's
`Scenario` / `BuyerPersona` types in types.ts field-for-field (snake_case
here; the frontend's fetch layer adapts to camelCase — see
frontend/src/api/scenario.ts).
"""
from pydantic import BaseModel, ConfigDict


class BuyerPersonaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str


class CompetencyThresholdOut(BaseModel):
    """Exposed even though the frontend's Scenario type doesn't consume it
    yet — the readiness engine (Phase 9) and result screen need exactly
    this data, and it's the same query already run for the scenario detail,
    so there's no reason to add a second endpoint later for it."""

    model_config = ConfigDict(from_attributes=True)

    competency_key: str
    display_name: str
    min_score: int


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    buyer_persona: BuyerPersonaOut
    product_context: str
    known_objection: str
    difficulty: str
    max_turns: int


class ScenarioDetailOut(ScenarioOut):
    thresholds: list[CompetencyThresholdOut]
