"""
Scenario read queries + MVP seed data.

Phase 5 scope only: the single Enterprise CFO scenario defined in
PHASE_0_PRODUCT_STRATEGY.md §2/§7, plus the 3 MVP competencies
(Discovery, Objection Handling, Closing) and their scenario-specific
thresholds. No scenario *creation* API — the MVP ships with exactly one
hardcoded scenario, per the Phase 0 Scope Gate. A scenario-authoring API
is out of scope until a later milestone actually needs more than one.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import BuyerPersona, Competency, Scenario, ScenarioCompetencyThreshold
from app.scenario.schemas import CompetencyThresholdOut, ScenarioDetailOut, ScenarioOut

# --------------------------------------------------------------------------
# MVP seed data
# --------------------------------------------------------------------------
# Thresholds chosen per Phase 0/9 intent: this scenario should read as a
# *believable* NOT_READY case out of the box (Objection Handling threshold
# set deliberately high, since price objection handling is this scenario's
# named challenge — see `known_objection` below), not a scenario every
# mock run trivially passes. Exact values are a product judgment call,
# recorded here (not buried in a migration) so Phase 9 tests and this seed
# stay obviously in sync. Revisit if Phase 15 stress testing shows these
# don't produce a sane READY/NOT_READY/AT_RISK spread.
_MVP_COMPETENCIES = [
    ("discovery", "Discovery", 60),
    ("objection_handling", "Objection Handling", 70),
    ("closing", "Closing", 65),
]

_MVP_PERSONA_NAME = "Enterprise CFO"


def seed_mvp_scenario(db: Session) -> None:
    """Idempotent: safe to call on every dev startup. Does nothing if the
    MVP scenario already exists, so it never creates duplicates or clobbers
    thresholds a later phase might adjust in the DB directly."""
    existing = db.execute(select(Scenario).limit(1)).scalar_one_or_none()
    if existing is not None:
        return

    persona = BuyerPersona(
        name=_MVP_PERSONA_NAME,
        description=(
            "High sophistication. Primary concern is ROI and budget-cycle risk. "
            "Will raise a pricing objection early and push back on vague answers."
        ),
        base_state={"trust": 45, "patience": 60, "budget_sensitivity": 80, "interest": 55},
    )
    db.add(persona)
    db.flush()  # need persona.id before creating the scenario

    scenario = Scenario(
        title="Enterprise CFO — Price Objection",
        buyer_persona_id=persona.id,
        product_context=(
            "AI-powered CRM platform, positioned against Salesforce for a 400-seat enterprise deal."
        ),
        known_objection="Price — currently evaluating a cheaper competitor.",
        difficulty="standard",
        max_turns=12,
    )
    db.add(scenario)
    db.flush()

    competencies_by_key: dict[str, Competency] = {}
    for key, display_name, _min_score in _MVP_COMPETENCIES:
        competency = Competency(key=key, display_name=display_name)
        db.add(competency)
        competencies_by_key[key] = competency
    db.flush()

    for key, _display_name, min_score in _MVP_COMPETENCIES:
        db.add(
            ScenarioCompetencyThreshold(
                scenario_id=scenario.id,
                competency_id=competencies_by_key[key].id,
                min_score=min_score,
            )
        )

    db.commit()


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------


def list_scenarios(db: Session) -> list[ScenarioOut]:
    scenarios = db.execute(
        select(Scenario).options(joinedload(Scenario.buyer_persona))
    ).scalars().all()
    return [ScenarioOut.model_validate(s) for s in scenarios]


def get_scenario(db: Session, scenario_id: str) -> ScenarioDetailOut | None:
    scenario = db.execute(
        select(Scenario)
        .where(Scenario.id == scenario_id)
        .options(
            joinedload(Scenario.buyer_persona),
            joinedload(Scenario.thresholds).joinedload(ScenarioCompetencyThreshold.competency),
        )
    ).unique().scalar_one_or_none()

    if scenario is None:
        return None

    thresholds = [
        CompetencyThresholdOut(
            competency_key=t.competency.key,
            display_name=t.competency.display_name,
            min_score=t.min_score,
        )
        for t in scenario.thresholds
    ]

    return ScenarioDetailOut(
        id=scenario.id,
        title=scenario.title,
        buyer_persona=scenario.buyer_persona,
        product_context=scenario.product_context,
        known_objection=scenario.known_objection,
        difficulty=scenario.difficulty,
        max_turns=scenario.max_turns,
        thresholds=thresholds,
    )
