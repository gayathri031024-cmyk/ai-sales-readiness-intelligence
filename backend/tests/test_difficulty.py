"""
Phase 12 — Adaptive Difficulty: a deterministic (zero-LLM) recommendation
of the next scenario difficulty (easy/standard/hard), built entirely
from Phase 9's already-computed readiness verdict and Phase 8's
already-persisted per-competency scores/thresholds.

Mirrors test_readiness.py's/test_drills.py's organization (the other
zero-LLM modules): pure unit-level tests for `decision.py`, and full
API-level tests for the read-only endpoint. No LLM degradation tests
are needed here for the same reason none were needed for readiness or
drills — this module makes no LLM calls at all, which is itself
asserted directly.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.ai.provider import MockLLMProvider
from app.api.routes.conversation import get_llm_provider
from app.difficulty.decision import (
    DIFFICULTY_LEVELS,
    NoCompetencyResultsError,
    READY_COMFORTABLE_MARGIN,
    UnknownDifficultyError,
    recommend_difficulty,
)
from app.main import app
from app.readiness.decision import CompetencyResult

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
    return json.dumps(
        {
            "evidence": [
                {"turn_index": 1, "competency_key": "discovery", "quote": "Discovery line."},
                {"turn_index": 3, "competency_key": "objection_handling", "quote": "Objection line."},
                {"turn_index": 5, "competency_key": "closing", "quote": "Closing line."},
            ]
        }
    )


def _start_evaluate_and_ready(client, scenario_id, mock_provider, scores: dict[str, int]) -> str:
    """Creates a conversation, submits one rep turn per MVP competency,
    closes it, evaluates with the given exact scores, then computes
    readiness — everything Phase 12 requires as a precondition.
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
    assert client.post(f"/conversations/{conversation_id}/evaluate").status_code == 200
    assert client.post(f"/conversations/{conversation_id}/readiness").status_code == 200
    return conversation_id


_DISPLAY_NAMES = {"discovery": "Discovery", "objection_handling": "Objection Handling", "closing": "Closing"}


def _result(key: str, score: int, min_score: int) -> CompetencyResult:
    return CompetencyResult(competency_key=key, display_name=_DISPLAY_NAMES[key], score=score, min_score=min_score)


# --------------------------------------------------------------------
# Unit-level: recommend_difficulty (pure function, no DB/HTTP/LLM)
# --------------------------------------------------------------------


def test_recommend_difficulty_not_ready_steps_down():
    results = [_result("discovery", 20, 60), _result("objection_handling", 85, 70), _result("closing", 90, 65)]
    rec = recommend_difficulty(results, "NOT_READY", "standard")
    assert rec.direction == "decrease"
    assert rec.recommended_difficulty == "easy"
    assert rec.current_difficulty == "standard"
    assert rec.verdict == "NOT_READY"
    assert "NOT_READY" in rec.reasoning


def test_recommend_difficulty_not_ready_at_floor_stays_at_easy():
    results = [_result("discovery", 20, 60), _result("objection_handling", 85, 70), _result("closing", 90, 65)]
    rec = recommend_difficulty(results, "NOT_READY", "easy")
    assert rec.direction == "maintain"
    assert rec.recommended_difficulty == "easy"
    assert "lowest difficulty" in rec.reasoning


def test_recommend_difficulty_at_risk_stays_put():
    results = [_result("discovery", 80, 60), _result("objection_handling", 63, 70), _result("closing", 90, 65)]
    rec = recommend_difficulty(results, "AT_RISK", "standard")
    assert rec.direction == "maintain"
    assert rec.recommended_difficulty == "standard"
    assert "AT_RISK" in rec.reasoning


def test_recommend_difficulty_ready_narrow_margin_stays_put():
    # Narrowest passing margin: discovery scored 61 vs. min 60 -> margin 1, well below READY_COMFORTABLE_MARGIN.
    results = [_result("discovery", 61, 60), _result("objection_handling", 85, 70), _result("closing", 90, 65)]
    rec = recommend_difficulty(results, "READY", "standard")
    assert rec.direction == "maintain"
    assert rec.recommended_difficulty == "standard"
    assert "narrowly" in rec.reasoning


def test_recommend_difficulty_ready_comfortable_margin_steps_up():
    results = [_result("discovery", 90, 60), _result("objection_handling", 90, 70), _result("closing", 90, 65)]
    rec = recommend_difficulty(results, "READY", "standard")
    assert rec.direction == "increase"
    assert rec.recommended_difficulty == "hard"
    assert "comfortable margin" in rec.reasoning


def test_recommend_difficulty_ready_comfortable_margin_at_ceiling_stays_at_hard():
    results = [_result("discovery", 90, 60), _result("objection_handling", 90, 70), _result("closing", 90, 65)]
    rec = recommend_difficulty(results, "READY", "hard")
    assert rec.direction == "maintain"
    assert rec.recommended_difficulty == "hard"
    assert "highest difficulty" in rec.reasoning


def test_recommend_difficulty_boundary_margin_exactly_at_threshold_steps_up():
    # Narrowest margin exactly READY_COMFORTABLE_MARGIN (10) counts as comfortable, not narrow.
    results = [
        _result("discovery", 60 + READY_COMFORTABLE_MARGIN, 60),
        _result("objection_handling", 90, 70),
        _result("closing", 90, 65),
    ]
    rec = recommend_difficulty(results, "READY", "standard")
    assert rec.direction == "increase"
    assert rec.recommended_difficulty == "hard"


def test_recommend_difficulty_boundary_margin_one_below_threshold_stays_put():
    results = [
        _result("discovery", 60 + READY_COMFORTABLE_MARGIN - 1, 60),
        _result("objection_handling", 90, 70),
        _result("closing", 90, 65),
    ]
    rec = recommend_difficulty(results, "READY", "standard")
    assert rec.direction == "maintain"
    assert rec.recommended_difficulty == "standard"


def test_recommend_difficulty_raises_on_empty_results():
    with pytest.raises(NoCompetencyResultsError):
        recommend_difficulty([], "READY", "standard")


def test_recommend_difficulty_raises_on_unknown_current_difficulty():
    results = [_result("discovery", 80, 60)]
    with pytest.raises(UnknownDifficultyError):
        recommend_difficulty(results, "READY", "medium")


def test_recommend_difficulty_is_deterministic_across_repeated_calls():
    results = [_result("discovery", 80, 60), _result("objection_handling", 30, 70), _result("closing", 90, 65)]
    first = recommend_difficulty(results, "NOT_READY", "standard")
    second = recommend_difficulty(results, "NOT_READY", "standard")
    assert first == second


@pytest.mark.parametrize(
    ("verdict", "current"),
    [
        ("NOT_READY", "easy"),
        ("NOT_READY", "standard"),
        ("NOT_READY", "hard"),
        ("AT_RISK", "easy"),
        ("AT_RISK", "standard"),
        ("AT_RISK", "hard"),
        ("READY", "easy"),
        ("READY", "standard"),
        ("READY", "hard"),
    ],
)
def test_recommend_difficulty_always_returns_a_valid_difficulty_level(verdict, current):
    results = [_result("discovery", 80, 60), _result("objection_handling", 75, 70), _result("closing", 90, 65)]
    rec = recommend_difficulty(results, verdict, current)
    assert rec.recommended_difficulty in DIFFICULTY_LEVELS
    assert rec.direction in ("increase", "maintain", "decrease")


def test_recommend_difficulty_never_calls_anything_ai_related():
    # No provider argument even exists in recommend_difficulty's
    # signature — this test exists mainly as a living assertion that
    # stays true only as long as that remains the case (a signature
    # change adding a provider parameter would break this test
    # immediately). Mirrors test_drills.py's identical pattern.
    import inspect

    params = inspect.signature(recommend_difficulty).parameters
    assert "provider" not in params
    assert "llm" not in " ".join(params).lower()


# --------------------------------------------------------------------
# API-level: full pipeline (evaluate -> readiness -> difficulty)
# --------------------------------------------------------------------


def test_difficulty_recommendation_ready_comfortable_recommends_increase(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_ready(
        client, scenario_id, mock_provider, {"discovery": 90, "objection_handling": 90, "closing": 90}
    )
    response = client.get(f"/conversations/{conversation_id}/difficulty-recommendation")
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "READY"
    assert body["current_difficulty"] == "standard"  # the seeded MVP scenario
    assert body["recommended_difficulty"] == "hard"
    assert body["direction"] == "increase"
    assert body["conversation_id"] == conversation_id


def test_difficulty_recommendation_ready_narrow_recommends_maintain(client, scenario_id, mock_provider):
    # discovery threshold 60 — scoring 61 is the narrowest passing margin (1 point).
    conversation_id = _start_evaluate_and_ready(
        client, scenario_id, mock_provider, {"discovery": 61, "objection_handling": 85, "closing": 90}
    )
    response = client.get(f"/conversations/{conversation_id}/difficulty-recommendation")
    body = response.json()
    assert body["verdict"] == "READY"
    assert body["direction"] == "maintain"
    assert body["recommended_difficulty"] == "standard"


def test_difficulty_recommendation_at_risk_recommends_maintain(client, scenario_id, mock_provider):
    # closing threshold 65 — scoring 58 misses by 7, within AT_RISK_MARGIN (10).
    conversation_id = _start_evaluate_and_ready(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 58}
    )
    response = client.get(f"/conversations/{conversation_id}/difficulty-recommendation")
    body = response.json()
    assert body["verdict"] == "AT_RISK"
    assert body["direction"] == "maintain"
    assert body["recommended_difficulty"] == "standard"


def test_difficulty_recommendation_not_ready_recommends_decrease(client, scenario_id, mock_provider):
    # objection_handling threshold 70 — scoring 30 misses by 40, well past AT_RISK_MARGIN.
    conversation_id = _start_evaluate_and_ready(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    response = client.get(f"/conversations/{conversation_id}/difficulty-recommendation")
    body = response.json()
    assert body["verdict"] == "NOT_READY"
    assert body["direction"] == "decrease"
    assert body["recommended_difficulty"] == "easy"


def test_difficulty_recommendation_schema_has_expected_fields(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_ready(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    body = client.get(f"/conversations/{conversation_id}/difficulty-recommendation").json()
    assert set(body.keys()) == {
        "conversation_id",
        "verdict",
        "current_difficulty",
        "recommended_difficulty",
        "direction",
        "reasoning",
    }


def test_difficulty_recommendation_never_exposes_hidden_buyer_state(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_ready(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    body = client.get(f"/conversations/{conversation_id}/difficulty-recommendation").json()
    serialized = json.dumps(body)
    for leaked_field in ("trust", "patience", "budget_sensitivity", "current_buyer_state", "system_prompt"):
        assert leaked_field not in serialized


# --------------------------------------------------------------------
# Zero-LLM guarantee
# --------------------------------------------------------------------


def test_difficulty_recommendation_makes_zero_llm_calls(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_ready(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    calls_before = len(mock_provider.calls)
    client.get(f"/conversations/{conversation_id}/difficulty-recommendation")
    client.get(f"/conversations/{conversation_id}/difficulty-recommendation")
    assert len(mock_provider.calls) == calls_before  # difficulty recommendation never touches the LLM


# --------------------------------------------------------------------
# Determinism / repeatability at the API level (no persistence exists,
# so "idempotency" here means "same inputs always produce the same
# output," not "a second call returns a cached row")
# --------------------------------------------------------------------


def test_difficulty_recommendation_is_identical_across_repeated_api_calls(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_ready(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    first = client.get(f"/conversations/{conversation_id}/difficulty-recommendation").json()
    second = client.get(f"/conversations/{conversation_id}/difficulty-recommendation").json()
    assert first == second


# --------------------------------------------------------------------
# Precondition / error handling
# --------------------------------------------------------------------


def test_difficulty_recommendation_requires_readiness_first(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    client.post(f"/conversations/{conversation_id}/close")  # closed, but never evaluated/assessed
    response = client.get(f"/conversations/{conversation_id}/difficulty-recommendation")
    assert response.status_code == 409


def test_get_difficulty_recommendation_unknown_conversation_returns_404(client):
    response = client.get("/conversations/does-not-exist/difficulty-recommendation")
    assert response.status_code == 404
