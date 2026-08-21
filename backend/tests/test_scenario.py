import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Scenario
from app.main import app
from app.scenario.service import seed_mvp_scenario


@pytest.fixture(scope="module")
def client():
    # Used as a context manager (not just `TestClient(app)`) so the
    # `lifespan` startup handler actually runs — that's what creates the
    # schema and seeds the MVP scenario for these tests. Without `with`,
    # startup never fires and every query below would hit "no such table".
    with TestClient(app) as c:
        yield c


def test_list_scenarios_returns_the_mvp_scenario(client):
    response = client.get("/scenarios")
    assert response.status_code == 200

    body = response.json()
    assert len(body) == 1

    scenario = body[0]
    assert scenario["title"] == "Enterprise CFO — Price Objection"
    assert scenario["buyer_persona"]["name"] == "Enterprise CFO"
    assert scenario["difficulty"] == "standard"
    assert scenario["max_turns"] == 12


def test_get_scenario_detail_includes_all_three_mvp_thresholds(client):
    scenario_id = client.get("/scenarios").json()[0]["id"]

    response = client.get(f"/scenarios/{scenario_id}")
    assert response.status_code == 200

    body = response.json()
    assert body["id"] == scenario_id

    keys = {t["competency_key"] for t in body["thresholds"]}
    assert keys == {"discovery", "objection_handling", "closing"}

    by_key = {t["competency_key"]: t["min_score"] for t in body["thresholds"]}
    assert by_key["objection_handling"] == 70


def test_get_scenario_404_for_unknown_id(client):
    response = client.get("/scenarios/does-not-exist")
    assert response.status_code == 404


def test_buyer_hidden_state_never_appears_in_scenario_responses(client):
    """Regression guard for ARCHITECTURE.md §6: buyer_persona.base_state is
    seed-only server data, not something any scenario endpoint should ever
    expose, even though it isn't per-conversation hidden state."""
    scenario_id = client.get("/scenarios").json()[0]["id"]
    detail = client.get(f"/scenarios/{scenario_id}").json()
    assert "base_state" not in detail["buyer_persona"]


def test_seed_mvp_scenario_is_idempotent():
    """Calling the seed twice must not create a second scenario row —
    the dev lifespan calls this on every startup, so this is the
    guarantee that keeps repeated dev restarts from duplicating data."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    try:
        seed_mvp_scenario(db)
        seed_mvp_scenario(db)
        count = len(db.execute(select(Scenario)).scalars().all())
        assert count == 1
    finally:
        db.close()
