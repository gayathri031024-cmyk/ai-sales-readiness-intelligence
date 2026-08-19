"""
Phase 11 — Targeted Drills: a deterministic (zero-LLM) reassembly of
Phase 8's evaluation diagnosis/recommendation and Phase 10's already-
verified coaching output into a focused practice assignment.

Mirrors test_readiness.py's organization (the other zero-LLM module):
pure unit-level tests for `generation.py`, and full API-level tests for
the pipeline end to end. No LLM degradation tests are needed here for
the same reason none were needed for readiness — this module makes no
LLM calls at all, which is itself asserted directly.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.ai.provider import MockLLMProvider
from app.api.routes.conversation import get_llm_provider
from app.db.base import SessionLocal
from app.db.models import Drill
from app.drills.generation import generate_drill
from app.main import app

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


def _start_evaluate_readiness_and_coach(client, scenario_id, mock_provider, scores: dict[str, int]) -> str:
    """Creates a conversation, submits one rep turn per MVP competency,
    closes it, evaluates with the given exact scores, computes readiness,
    then generates coaching with no points (the drill only needs
    coaching's priority pick + reason; focus_points filtering is tested
    separately with points present) — everything Phase 11 requires as a
    precondition."""
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

    mock_provider.responses = [_coaching_response()]
    assert client.post(f"/conversations/{conversation_id}/coaching").status_code == 200
    return conversation_id


# --------------------------------------------------------------------
# Unit-level: generate_drill (pure function, no DB/HTTP/LLM)
# --------------------------------------------------------------------


def test_generate_drill_builds_title_and_instructions_deterministically():
    result = generate_drill(
        priority_competency_key="objection_handling",
        priority_display_name="Objection Handling",
        priority_reason="This competency has the largest gap: scored 30, needed 70 (40 points).",
        diagnosis="Rep did not address the price objection directly.",
        recommendation="Acknowledge the concern before pivoting to value.",
        coaching_points=[],
    )
    assert result.title == "Practice: Objection Handling"
    assert result.focus_reason == "This competency has the largest gap: scored 30, needed 70 (40 points)."
    assert "Objection Handling" in result.instructions
    assert "Rep did not address the price objection directly." in result.instructions
    assert "Acknowledge the concern before pivoting to value." in result.instructions
    assert result.focus_points == []


def test_generate_drill_filters_coaching_points_to_priority_competency_only():
    points = [
        {"competency_key": "discovery", "evidence_id": "e1", "message": "Ask more open questions."},
        {"competency_key": "objection_handling", "evidence_id": "e2", "message": "Name the objection out loud."},
        {"competency_key": "objection_handling", "evidence_id": None, "message": "Slow down before responding."},
        {"competency_key": "closing", "evidence_id": "e3", "message": "Ask for the next step explicitly."},
    ]
    result = generate_drill(
        priority_competency_key="objection_handling",
        priority_display_name="Objection Handling",
        priority_reason="reason",
        diagnosis="diagnosis",
        recommendation="recommendation",
        coaching_points=points,
    )
    assert len(result.focus_points) == 2
    assert all(p.competency_key == "objection_handling" for p in result.focus_points)
    assert result.focus_points[0].message == "Name the objection out loud."
    assert result.focus_points[0].evidence_id == "e2"
    assert result.focus_points[1].evidence_id is None
    assert "Name the objection out loud." in result.instructions
    assert "Ask more open questions." not in result.instructions  # discovery point excluded
    assert "Ask for the next step explicitly." not in result.instructions  # closing point excluded


def test_generate_drill_never_calls_anything_ai_related():
    # No provider argument even exists in generate_drill's signature —
    # this test exists mainly as a living assertion that stays true only
    # as long as that remains the case (a signature change adding a
    # provider parameter would break this test immediately).
    import inspect

    from app.drills.generation import generate_drill as fn

    params = inspect.signature(fn).parameters
    assert "provider" not in params
    assert "llm" not in " ".join(params).lower()


# --------------------------------------------------------------------
# API-level: full pipeline (evaluate -> readiness -> coaching -> drill)
# --------------------------------------------------------------------


def test_drill_matches_coaching_priority_and_carries_diagnosis(client, scenario_id, mock_provider):
    # objection_handling threshold is 70 — scoring 30 makes it the
    # worst-gap competency, so coaching's priority pick (and therefore
    # the drill) should target it.
    conversation_id = _start_evaluate_readiness_and_coach(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    response = client.post(f"/conversations/{conversation_id}/drill")
    assert response.status_code == 200
    body = response.json()
    assert body["competency_key"] == "objection_handling"
    assert body["display_name"] == "Objection Handling"
    assert body["title"] == "Practice: Objection Handling"
    assert body["conversation_id"] == conversation_id
    assert "d" in body["instructions"]  # the mocked evaluation diagnosis text


def test_drill_practice_scenario_id_matches_origin_conversation_scenario(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_readiness_and_coach(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    body = client.post(f"/conversations/{conversation_id}/drill").json()
    assert body["practice_scenario_id"] == scenario_id


def test_drill_focus_points_come_from_persisted_coaching_points(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    for msg in ["Discovery line.", "Objection line.", "Closing line."]:
        mock_provider.responses = _turn_response()
        client.post(f"/conversations/{conversation_id}/turns", json={"message": msg})
    client.post(f"/conversations/{conversation_id}/close")

    mock_provider.responses = [
        _evidence_response(),
        _score_response(80),
        _score_response(30),  # objection_handling — worst gap, becomes the priority
        _score_response(90),
    ]
    client.post(f"/conversations/{conversation_id}/evaluate")
    client.post(f"/conversations/{conversation_id}/readiness")

    evidence_id = _evidence_id_for(client, conversation_id, "objection_handling")
    mock_provider.responses = [
        _coaching_response(
            points=[
                {"competency_key": "objection_handling", "evidence_id": evidence_id, "message": "Name it directly."},
                {"competency_key": "discovery", "evidence_id": None, "message": "Ask a bigger follow-up."},
            ]
        )
    ]
    client.post(f"/conversations/{conversation_id}/coaching")

    body = client.post(f"/conversations/{conversation_id}/drill").json()
    assert len(body["focus_points"]) == 1
    assert body["focus_points"][0]["message"] == "Name it directly."
    assert body["focus_points"][0]["competency_key"] == "objection_handling"


def _evidence_id_for(client, conversation_id: str, competency_key: str) -> str:
    result = client.get(f"/conversations/{conversation_id}/result").json()
    evaluation = next(e for e in result["evaluations"] if e["competency_key"] == competency_key)
    return evaluation["evidence"][0]["id"]


# --------------------------------------------------------------------
# Zero-LLM guarantee
# --------------------------------------------------------------------


def test_drill_generation_makes_zero_llm_calls(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_readiness_and_coach(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    calls_before = len(mock_provider.calls)
    client.post(f"/conversations/{conversation_id}/drill")
    client.get(f"/conversations/{conversation_id}/drill")
    assert len(mock_provider.calls) == calls_before  # drill generation never touches the LLM


# --------------------------------------------------------------------
# Precondition / error handling
# --------------------------------------------------------------------


def test_drill_requires_coaching_first(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    client.post(f"/conversations/{conversation_id}/close")  # closed, but never evaluated/coached
    response = client.post(f"/conversations/{conversation_id}/drill")
    assert response.status_code == 409


def test_post_drill_unknown_conversation_returns_404(client):
    response = client.post("/conversations/does-not-exist/drill")
    assert response.status_code == 404


def test_get_drill_404_before_it_has_been_generated(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_readiness_and_coach(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    # Coached, but POST .../drill never called yet.
    response = client.get(f"/conversations/{conversation_id}/drill")
    assert response.status_code == 404


def test_get_drill_returns_previously_generated_drill(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_readiness_and_coach(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    posted = client.post(f"/conversations/{conversation_id}/drill").json()
    fetched = client.get(f"/conversations/{conversation_id}/drill").json()
    assert posted == fetched


def test_get_drill_404_unknown_conversation(client):
    response = client.get("/conversations/does-not-exist/drill")
    assert response.status_code == 404


# --------------------------------------------------------------------
# Idempotency
# --------------------------------------------------------------------


def test_drill_is_idempotent_no_duplicate_rows(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_readiness_and_coach(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    first = client.post(f"/conversations/{conversation_id}/drill").json()
    second = client.post(f"/conversations/{conversation_id}/drill").json()
    assert first == second

    db = SessionLocal()
    try:
        rows = db.query(Drill).filter(Drill.conversation_id == conversation_id).all()
        assert len(rows) == 1
    finally:
        db.close()


# --------------------------------------------------------------------
# Hidden-state / system-prompt / internal-reasoning protection
# --------------------------------------------------------------------


def test_drill_response_never_exposes_hidden_buyer_state(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_readiness_and_coach(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    body = client.post(f"/conversations/{conversation_id}/drill").json()
    serialized = json.dumps(body)
    for field in ("trust", "patience", "budget_sensitivity", "interest", "current_buyer_state"):
        assert field not in serialized


def test_drill_response_never_exposes_system_prompt_or_internal_reasoning(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_readiness_and_coach(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    body = client.post(f"/conversations/{conversation_id}/drill").json()
    serialized = json.dumps(body).lower()
    for phrase in ("system prompt", "internal reasoning", "chain of thought", "classified_intent"):
        assert phrase not in serialized


# --------------------------------------------------------------------
# Public API response schema
# --------------------------------------------------------------------


def test_drill_response_schema_has_expected_fields(client, scenario_id, mock_provider):
    conversation_id = _start_evaluate_readiness_and_coach(
        client, scenario_id, mock_provider, {"discovery": 80, "objection_handling": 30, "closing": 90}
    )
    body = client.post(f"/conversations/{conversation_id}/drill").json()
    assert set(body.keys()) == {
        "id",
        "conversation_id",
        "competency_key",
        "display_name",
        "practice_scenario_id",
        "title",
        "focus_reason",
        "instructions",
        "focus_points",
        "created_at",
    }
