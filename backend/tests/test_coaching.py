"""
Phase 10 — AI Coach: deterministic priority selection (no LLM) plus an
evidence-grounded LLM-generated coaching narrative, built from Phase 8's
persisted evaluations/evidence and Phase 9's persisted readiness verdict.

Mirrors test_readiness.py's organization: pure unit-level tests for the
deterministic pieces (`priority.py`, `verification.py`), and full
API-level tests for the pipeline end to end.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.ai.provider import MockLLMProvider
from app.api.routes.conversation import get_llm_provider
from app.coaching.generation import CoachingPointCandidate
from app.coaching.priority import NoCompetencyResultsError, pick_priority
from app.coaching.verification import verify_coaching_points
from app.db.base import SessionLocal
from app.db.models import CoachingSession
from app.main import app
from app.readiness.decision import CompetencyResult

MVP_ORDER = ("discovery", "objection_handling", "closing")

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


def _coaching_response(points: list[dict] | None = None, summary: str = "Solid overall, focus here next.") -> str:
    return json.dumps({"summary": summary, "points": points if points is not None else []})


def _start_evaluate_and_assess(client, scenario_id, mock_provider, scores: dict[str, int]) -> str:
    """Creates a conversation, submits one rep turn per MVP competency,
    closes it, evaluates with the given exact scores, then computes
    readiness — everything Phase 10 coaching requires as a precondition."""
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


def _evidence_id_for(client, conversation_id: str, competency_key: str) -> str:
    result = client.get(f"/conversations/{conversation_id}/result").json()
    evaluation = next(e for e in result["evaluations"] if e["competency_key"] == competency_key)
    return evaluation["evidence"][0]["id"]


# --------------------------------------------------------------------
# Unit-level: pick_priority (pure function, no DB/HTTP/LLM)
# --------------------------------------------------------------------


def _result(key: str, score: int, min_score: int) -> CompetencyResult:
    names = {"discovery": "Discovery", "objection_handling": "Objection Handling", "closing": "Closing"}
    return CompetencyResult(competency_key=key, display_name=names[key], score=score, min_score=min_score)


def test_pick_priority_picks_worst_gap_when_something_fails():
    results = [
        _result("discovery", 80, 60),  # passes, gap -20
        _result("objection_handling", 30, 70),  # fails, gap 40 (worst)
        _result("closing", 55, 65),  # fails, gap 10
    ]
    pick = pick_priority(results, MVP_ORDER)
    assert pick.competency_key == "objection_handling"
    assert "largest gap" in pick.reason
    assert "40 points" in pick.reason


def test_pick_priority_picks_narrowest_margin_when_all_pass():
    results = [
        _result("discovery", 90, 60),  # margin 30
        _result("objection_handling", 72, 70),  # margin 2 (narrowest)
        _result("closing", 85, 65),  # margin 20
    ]
    pick = pick_priority(results, MVP_ORDER)
    assert pick.competency_key == "objection_handling"
    assert "narrowest margin" in pick.reason


def test_pick_priority_breaks_ties_by_mvp_order():
    # Two competencies fail by an identical gap of 10 — discovery comes
    # first in MVP_ORDER, so it should win the tie.
    results = [
        _result("closing", 55, 65),  # gap 10
        _result("discovery", 50, 60),  # gap 10, earlier in MVP_ORDER
        _result("objection_handling", 90, 70),  # passes
    ]
    pick = pick_priority(results, MVP_ORDER)
    assert pick.competency_key == "discovery"


def test_pick_priority_raises_on_empty_results():
    with pytest.raises(NoCompetencyResultsError):
        pick_priority([], MVP_ORDER)


# --------------------------------------------------------------------
# Unit-level: verify_coaching_points (pure function, no DB/HTTP/LLM)
# --------------------------------------------------------------------


def test_verify_coaching_points_accepts_a_valid_evidence_reference():
    candidates = [CoachingPointCandidate(competency_key="discovery", evidence_id="ev-1", message="Nice work.")]
    verified = verify_coaching_points(candidates, {"discovery": {"ev-1", "ev-2"}}, {"discovery"})
    assert len(verified) == 1
    assert verified[0].evidence_id == "ev-1"


def test_verify_coaching_points_rejects_a_fabricated_evidence_id():
    candidates = [CoachingPointCandidate(competency_key="discovery", evidence_id="ev-fake", message="Nice work.")]
    verified = verify_coaching_points(candidates, {"discovery": {"ev-1", "ev-2"}}, {"discovery"})
    assert verified == []


def test_verify_coaching_points_rejects_evidence_id_from_a_different_competency():
    # ev-3 is real, but only for objection_handling — citing it under
    # discovery is still a fabricated reference for THIS competency.
    candidates = [CoachingPointCandidate(competency_key="discovery", evidence_id="ev-3", message="Nice work.")]
    verified = verify_coaching_points(
        candidates, {"discovery": {"ev-1"}, "objection_handling": {"ev-3"}}, {"discovery", "objection_handling"}
    )
    assert verified == []


def test_verify_coaching_points_rejects_competency_not_evaluated_this_conversation():
    candidates = [CoachingPointCandidate(competency_key="closing", evidence_id=None, message="Nice work.")]
    verified = verify_coaching_points(candidates, {}, {"discovery", "objection_handling"})
    assert verified == []


def test_verify_coaching_points_allows_null_evidence_id_through_unchanged():
    candidates = [CoachingPointCandidate(competency_key="discovery", evidence_id=None, message="Keep at it.")]
    verified = verify_coaching_points(candidates, {"discovery": {"ev-1"}}, {"discovery"})
    assert len(verified) == 1
    assert verified[0].evidence_id is None


# --------------------------------------------------------------------
# API-level: full pipeline (evaluate -> readiness -> coaching)
# --------------------------------------------------------------------


def test_coaching_priority_matches_worst_failing_competency(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 20, "closing": 90}
    )
    mock_provider.responses = [_coaching_response()]
    response = client.post(f"/conversations/{conversation_id}/coaching")
    assert response.status_code == 200
    body = response.json()
    assert body["priority_competency_key"] == "objection_handling"
    assert "largest gap" in body["priority_reason"]


def test_coaching_grounded_point_persists_with_real_evidence_id(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 20, "closing": 90}
    )
    real_evidence_id = _evidence_id_for(client, conversation_id, "objection_handling")

    mock_provider.responses = [
        _coaching_response(
            points=[
                {
                    "competency_key": "objection_handling",
                    "evidence_id": real_evidence_id,
                    "message": "Acknowledge the concern before pivoting.",
                }
            ]
        )
    ]
    body = client.post(f"/conversations/{conversation_id}/coaching").json()
    assert len(body["points"]) == 1
    assert body["points"][0]["evidence_id"] == real_evidence_id
    assert body["points"][0]["competency_key"] == "objection_handling"


def test_coaching_point_with_fabricated_evidence_id_never_reaches_the_api_response(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 20, "closing": 90}
    )
    mock_provider.responses = [
        _coaching_response(
            points=[
                {
                    "competency_key": "objection_handling",
                    "evidence_id": "not-a-real-evidence-id",
                    "message": "You confidently quoted a 20% discount.",
                }
            ]
        )
    ]
    body = client.post(f"/conversations/{conversation_id}/coaching").json()
    assert body["points"] == []
    assert "not-a-real-evidence-id" not in json.dumps(body)


# --------------------------------------------------------------------
# Graceful degradation
# --------------------------------------------------------------------


def test_coaching_falls_back_to_deterministic_summary_when_llm_completely_unavailable(
    client, scenario_id, mock_provider
):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 20, "closing": 90}
    )
    mock_provider.always_fail = True

    response = client.post(f"/conversations/{conversation_id}/coaching")
    assert response.status_code == 200
    body = response.json()
    # Priority selection is deterministic and doesn't depend on the LLM,
    # so it must still be correct even with the LLM fully down.
    assert body["priority_competency_key"] == "objection_handling"
    assert body["points"] == []
    assert "Objection Handling" in body["summary"]  # built from the same deterministic data


def test_coaching_retries_once_on_malformed_json_then_succeeds(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    mock_provider.responses = ["not valid json at all", _coaching_response(summary="Recovered fine.")]
    body = client.post(f"/conversations/{conversation_id}/coaching").json()
    assert body["summary"] == "Recovered fine."


# --------------------------------------------------------------------
# Preconditions / error handling
# --------------------------------------------------------------------


def test_coaching_requires_readiness_first(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    client.post(f"/conversations/{conversation_id}/close")
    mock_provider.responses = [_evidence_response()]
    client.post(f"/conversations/{conversation_id}/evaluate")
    # Evaluated, but readiness was never computed.
    response = client.post(f"/conversations/{conversation_id}/coaching")
    assert response.status_code == 409


def test_post_coaching_unknown_conversation_returns_404(client):
    response = client.post("/conversations/does-not-exist/coaching")
    assert response.status_code == 404


def test_get_coaching_404_before_it_has_been_generated(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    response = client.get(f"/conversations/{conversation_id}/coaching")
    assert response.status_code == 404


def test_get_coaching_returns_previously_generated_session(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    mock_provider.responses = [_coaching_response()]
    posted = client.post(f"/conversations/{conversation_id}/coaching").json()
    fetched = client.get(f"/conversations/{conversation_id}/coaching").json()
    assert posted == fetched


def test_get_coaching_404_unknown_conversation(client):
    response = client.get("/conversations/does-not-exist/coaching")
    assert response.status_code == 404


# --------------------------------------------------------------------
# Idempotency
# --------------------------------------------------------------------


def test_coaching_is_idempotent_no_duplicate_rows_and_no_repeat_llm_calls(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    mock_provider.responses = [_coaching_response(summary="First generation.")]
    calls_before = len(mock_provider.calls)
    first = client.post(f"/conversations/{conversation_id}/coaching").json()
    calls_after_first = len(mock_provider.calls)

    # No new responses queued — a second real LLM call would fall
    # through to the empty default and fail schema validation.
    second = client.post(f"/conversations/{conversation_id}/coaching").json()

    assert first == second
    assert len(mock_provider.calls) == calls_after_first  # no new LLM call made
    assert calls_after_first > calls_before  # sanity: the first call did use the LLM

    db = SessionLocal()
    try:
        rows = db.query(CoachingSession).filter(CoachingSession.conversation_id == conversation_id).all()
        assert len(rows) == 1
    finally:
        db.close()


# --------------------------------------------------------------------
# Hidden-state / security protection
# --------------------------------------------------------------------


def test_coaching_response_never_exposes_hidden_buyer_state(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    mock_provider.responses = [_coaching_response()]
    body = client.post(f"/conversations/{conversation_id}/coaching").json()
    serialized = json.dumps(body)
    for field in ("trust", "patience", "budget_sensitivity", "interest", "current_buyer_state"):
        assert field not in serialized


def test_coaching_response_never_exposes_system_prompt_or_internal_reasoning(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    mock_provider.responses = [_coaching_response()]
    body = client.post(f"/conversations/{conversation_id}/coaching").json()
    serialized = json.dumps(body).lower()
    for phrase in ("system prompt", "internal reasoning", "chain of thought", "classified_intent"):
        assert phrase not in serialized


# --------------------------------------------------------------------
# Public API response schema
# --------------------------------------------------------------------


def test_coaching_response_schema_has_expected_fields(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_and_assess(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 85, "closing": 90}
    )
    real_evidence_id = _evidence_id_for(client, conversation_id, "discovery")
    mock_provider.responses = [
        _coaching_response(
            points=[{"competency_key": "discovery", "evidence_id": real_evidence_id, "message": "Good open."}]
        )
    ]
    body = client.post(f"/conversations/{conversation_id}/coaching").json()
    assert set(body.keys()) == {
        "id",
        "conversation_id",
        "priority_competency_key",
        "priority_reason",
        "summary",
        "points",
        "created_at",
    }
    assert set(body["points"][0].keys()) == {"competency_key", "evidence_id", "message"}


# --------------------------------------------------------------------
# Regression — Phase 0-9 tests still pass alongside these (verified by
# running the full suite together, not re-implemented here).
# --------------------------------------------------------------------
