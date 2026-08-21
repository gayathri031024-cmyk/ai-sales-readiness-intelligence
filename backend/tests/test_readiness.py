"""
Phase 9 — Readiness Engine: the deterministic READY/NOT_READY/AT_RISK
decision built from Phase 8's persisted competency scores and Phase 5's
seeded scenario-specific thresholds (discovery=60, objection_handling=70,
closing=65 — see scenario/service.py's `_MVP_COMPETENCIES`).

This module never calls an LLM (ARCHITECTURE.md §3) — the only MockLLMProvider
usage in this file is to drive Phase 8's evaluation step so there's
something for readiness to read. `decide_readiness` itself is exercised
both as a pure unit-level function (no DB, no HTTP) and through the full
API, mirroring the project's existing test-organization convention.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.ai.provider import MockLLMProvider
from app.api.routes.conversation import get_llm_provider
from app.db.base import SessionLocal
from app.db.models import ReadinessResult
from app.main import app
from app.readiness.decision import (
    AT_RISK_MARGIN,
    CompetencyResult,
    NoCompetencyResultsError,
    decide_readiness,
)

# --------------------------------------------------------------------
# Shared fixtures / helpers
# --------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_provider(client):
    provider = MockLLMProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    yield provider
    app.dependency_overrides.pop(get_llm_provider, None)


@pytest.fixture
def scenario_id(client):
    return client.get("/scenarios").json()[0]["id"]


def _turn_response(behavior: str = "discovery_question", reply: str = "Buyer reply.") -> list[str]:
    return [json.dumps({"behavior": behavior, "confidence": 0.9, "rationale": "note"}), reply]


def _score_response(score: int) -> str:
    return json.dumps({"score": score, "diagnosis": "d", "impact": "i", "recommendation": "r"})


def _evidence_response() -> str:
    # One grounded piece of evidence per MVP competency, citing turns
    # 1/3/5 — the rep turns `_start_and_evaluate` below always submits.
    return json.dumps(
        {
            "evidence": [
                {"turn_index": 1, "competency_key": "discovery", "quote": "Discovery line."},
                {"turn_index": 3, "competency_key": "objection_handling", "quote": "Objection line."},
                {"turn_index": 5, "competency_key": "closing", "quote": "Closing line."},
            ]
        }
    )


def _start_and_evaluate(client, scenario_id, mock_provider, scores: dict[str, int]) -> str:
    """Creates a conversation, submits one rep turn per MVP competency
    (so each competency has grounded evidence and therefore an
    LLM-scored result, not the deterministic no-evidence path), closes
    it, then runs Phase 8 evaluation with the given exact scores.
    `scores` keys: "discovery", "objection_handling", "closing"."""
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    for msg in ["Discovery line.", "Objection line.", "Closing line."]:
        mock_provider.responses = _turn_response()
        client.post(f"/conversations/{conversation_id}/turns", json={"message": msg})
    client.post(f"/conversations/{conversation_id}/close")

    mock_provider.responses = [
        _evidence_response(),
        _score_response(scores["discovery"]),
        _score_response(scores["objection_handling"]),
        _score_response(scores["closing"]),
    ]
    response = client.post(f"/conversations/{conversation_id}/evaluate")
    assert response.status_code == 200
    return conversation_id


# --------------------------------------------------------------------
# Unit-level: decide_readiness (pure function, no DB/HTTP)
# --------------------------------------------------------------------


_DISPLAY_NAMES = {"discovery": "Discovery", "objection_handling": "Objection Handling", "closing": "Closing"}


def _result(key: str, score: int, min_score: int) -> CompetencyResult:
    return CompetencyResult(competency_key=key, display_name=_DISPLAY_NAMES[key], score=score, min_score=min_score)


def test_decide_readiness_all_pass_is_ready():
    results = [_result("discovery", 80, 60), _result("objection_handling", 90, 70), _result("closing", 70, 65)]
    decision = decide_readiness(results)
    assert decision.verdict == "READY"
    assert "required thresholds" in decision.reasoning.lower()


def test_decide_readiness_score_exactly_equal_to_threshold_passes():
    results = [_result("discovery", 60, 60), _result("objection_handling", 70, 70), _result("closing", 65, 65)]
    assert decide_readiness(results).verdict == "READY"


def test_decide_readiness_small_gap_is_at_risk():
    # Gap of exactly AT_RISK_MARGIN (10) still counts as borderline, not a clear miss.
    results = [
        _result("discovery", 80, 60),
        _result("objection_handling", 70 - AT_RISK_MARGIN, 70),
        _result("closing", 70, 65),
    ]
    decision = decide_readiness(results)
    assert decision.verdict == "AT_RISK"
    assert "Objection Handling scored" in decision.reasoning


def test_decide_readiness_large_gap_is_not_ready():
    # Gap of AT_RISK_MARGIN + 1 is a clear miss, not borderline.
    results = [
        _result("discovery", 80, 60),
        _result("objection_handling", 70 - AT_RISK_MARGIN - 1, 70),
        _result("closing", 70, 65),
    ]
    assert decide_readiness(results).verdict == "NOT_READY"


def test_decide_readiness_reasoning_names_every_failing_competency():
    results = [_result("discovery", 10, 60), _result("objection_handling", 20, 70), _result("closing", 70, 65)]
    decision = decide_readiness(results)
    assert decision.verdict == "NOT_READY"
    assert "Discovery scored 10" in decision.reasoning
    assert "Objection Handling scored 20" in decision.reasoning
    assert "Closing" not in decision.reasoning.split("Objection Handling")[0]  # closing passed, not named


def test_decide_readiness_raises_on_empty_results():
    with pytest.raises(NoCompetencyResultsError):
        decide_readiness([])


def test_competency_result_gap_and_passed():
    passing = CompetencyResult(competency_key="discovery", display_name="Discovery", score=70, min_score=60)
    failing = CompetencyResult(competency_key="discovery", display_name="Discovery", score=50, min_score=60)
    assert passing.passed is True
    assert passing.gap == -10
    assert failing.passed is False
    assert failing.gap == 10


# --------------------------------------------------------------------
# API-level: full pipeline (evaluate -> readiness)
# --------------------------------------------------------------------


def test_readiness_ready_when_all_competencies_pass(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    response = client.post(f"/conversations/{conversation_id}/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "READY"
    assert body["conversation_id"] == conversation_id


def test_readiness_not_ready_when_a_competency_misses_by_a_wide_margin(client, scenario_id, mock_provider):
    # objection_handling threshold is 70 — scoring 30 misses by 40, well past AT_RISK_MARGIN.
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    response = client.post(f"/conversations/{conversation_id}/readiness")
    body = response.json()
    assert body["verdict"] == "NOT_READY"
    assert "Objection Handling scored 30" in body["reasoning"]
    assert "below the required minimum of 70" in body["reasoning"]


def test_readiness_at_risk_when_a_competency_misses_by_a_narrow_margin(client, scenario_id, mock_provider):
    # closing threshold is 65 — scoring 58 misses by 7, within AT_RISK_MARGIN (10).
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 58}
    )
    response = client.post(f"/conversations/{conversation_id}/readiness")
    body = response.json()
    assert body["verdict"] == "AT_RISK"


def test_readiness_requires_evaluation_first(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    client.post(f"/conversations/{conversation_id}/close")  # closed, but never evaluated
    response = client.post(f"/conversations/{conversation_id}/readiness")
    assert response.status_code == 409


def test_post_readiness_unknown_conversation_returns_404(client):
    response = client.post("/conversations/does-not-exist/readiness")
    assert response.status_code == 404


def test_get_readiness_404_before_it_has_been_computed(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    # Evaluated, but POST .../readiness never called yet.
    response = client.get(f"/conversations/{conversation_id}/readiness")
    assert response.status_code == 404


def test_get_readiness_returns_previously_computed_verdict(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    posted = client.post(f"/conversations/{conversation_id}/readiness").json()
    fetched = client.get(f"/conversations/{conversation_id}/readiness").json()
    assert posted == fetched


def test_get_readiness_404_unknown_conversation(client):
    response = client.get("/conversations/does-not-exist/readiness")
    assert response.status_code == 404


# --------------------------------------------------------------------
# Idempotency
# --------------------------------------------------------------------


def test_readiness_is_idempotent_no_duplicate_rows_and_verdict_does_not_drift(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    first = client.post(f"/conversations/{conversation_id}/readiness").json()
    second = client.post(f"/conversations/{conversation_id}/readiness").json()
    assert first == second

    db = SessionLocal()
    try:
        rows = db.query(ReadinessResult).filter(ReadinessResult.conversation_id == conversation_id).all()
        assert len(rows) == 1
    finally:
        db.close()


# --------------------------------------------------------------------
# GET .../result — combined evaluation + threshold + verdict
# --------------------------------------------------------------------


def test_get_result_lazily_computes_readiness_if_not_yet_explicitly_triggered(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    # No explicit POST .../readiness call before this GET.
    response = client.get(f"/conversations/{conversation_id}/result")
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "READY"

    db = SessionLocal()
    try:
        rows = db.query(ReadinessResult).filter(ReadinessResult.conversation_id == conversation_id).all()
        assert len(rows) == 1  # the lazy compute persisted exactly one row
    finally:
        db.close()


def test_get_result_includes_required_min_score_per_competency(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    body = client.get(f"/conversations/{conversation_id}/result").json()
    by_key = {e["competency_key"]: e for e in body["evaluations"]}
    assert by_key["discovery"]["required_min_score"] == 60
    assert by_key["objection_handling"]["required_min_score"] == 70
    assert by_key["closing"]["required_min_score"] == 65
    assert by_key["objection_handling"]["score"] == 30
    assert len(by_key["discovery"]["evidence"]) == 1


def test_get_result_404_when_conversation_not_yet_evaluated(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    client.post(f"/conversations/{conversation_id}/close")
    response = client.get(f"/conversations/{conversation_id}/result")
    assert response.status_code == 404


def test_get_result_404_unknown_conversation(client):
    response = client.get("/conversations/does-not-exist/result")
    assert response.status_code == 404


def test_get_result_schema_has_expected_fields(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    body = client.get(f"/conversations/{conversation_id}/result").json()
    assert set(body.keys()) == {"conversation_id", "verdict", "reasoning", "computed_at", "evaluations"}
    evaluation = body["evaluations"][0]
    assert set(evaluation.keys()) == {
        "id",
        "competency_key",
        "display_name",
        "score",
        "required_min_score",
        "diagnosis",
        "impact",
        "recommendation",
        "created_at",
        "evidence",
    }


# --------------------------------------------------------------------
# Hidden-state / no-LLM protection
# --------------------------------------------------------------------


def test_readiness_response_never_exposes_hidden_buyer_state(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    readiness_body = client.post(f"/conversations/{conversation_id}/readiness").json()
    result_body = client.get(f"/conversations/{conversation_id}/result").json()
    serialized = json.dumps(readiness_body) + json.dumps(result_body)
    for field in ("trust", "patience", "budget_sensitivity", "interest", "current_buyer_state"):
        assert field not in serialized


def test_readiness_computation_makes_zero_llm_calls(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    calls_before = len(mock_provider.calls)
    client.post(f"/conversations/{conversation_id}/readiness")
    client.get(f"/conversations/{conversation_id}/result")
    assert len(mock_provider.calls) == calls_before  # readiness never touches the LLM, per ARCHITECTURE.md §3


# --------------------------------------------------------------------
# Threshold snapshot persistence (DB-level)
# --------------------------------------------------------------------


def test_thresholds_snapshot_persisted_matches_actual_scenario_thresholds(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    client.post(f"/conversations/{conversation_id}/readiness")

    db = SessionLocal()
    try:
        row = db.query(ReadinessResult).filter(ReadinessResult.conversation_id == conversation_id).one()
        assert row.thresholds_snapshot == {"discovery": 60, "objection_handling": 70, "closing": 65}
        assert row.verdict == "READY"
    finally:
        db.close()


# --------------------------------------------------------------------
# Regression — Phase 0-8 tests still pass alongside these (verified by
# running the full suite together, not re-implemented here).
# --------------------------------------------------------------------
