from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.scenario import service
from app.scenario.schemas import ScenarioDetailOut, ScenarioOut

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioOut])
def list_scenarios(db: Session = Depends(get_db)) -> list[ScenarioOut]:
    """MVP: always returns exactly one scenario (the seeded Enterprise CFO
    scenario). Plural/list shape kept deliberately, even at n=1, so the
    frontend and any future scenario-picker UI don't need a breaking change
    when a second scenario is added post-MVP."""
    return service.list_scenarios(db)


@router.get("/{scenario_id}", response_model=ScenarioDetailOut)
def get_scenario(scenario_id: str, db: Session = Depends(get_db)) -> ScenarioDetailOut:
    scenario = service.get_scenario(db, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario
