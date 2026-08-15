"""
Phase 7 — Conversation Engine: persistence, multi-turn flow, end
conditions, and hidden-state protection.

Same MockLLMProvider-only discipline as the Phase 6 tests: no real
LLM_API_KEY / ANTHROPIC_API_KEY is ever required. The provider is
injected via FastAPI dependency override (`get_llm_provider`), the same
pattern `get_db` already uses for a test database.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.ai.provider import MockLLMProvider
from app.api.routes.conversation import get_llm_provider
from app.buyer.rules import get_delta_for
from app.buyer.classification import RepBehavior
from app.db.base import SessionLocal
from app.db.models import BuyerStateHistory
from app.main import app

_PERSONA_BASE_STATE = {"trust": 45, "patience": 60, "budget_sensitivity": 80, "interest": 55}


def _turn_response(behavior: str, reply: str) -> list[str]:
    """One queued classify+reply pair, same shape as test_buyer_graph.py's
    `_healthy_provider` helper."""
    return [json.dumps({"behavior": behavior, "confidence": 0.9, "rationale": "note"}), reply]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_provider(client):
    """A fresh MockLLMProvider per test, wired in via dependency override.
    Tests queue responses onto `provider.responses` before each call that
    needs one."""
    provider = MockLLMProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    yield provider
    app.dependency_overrides.pop(get_llm_provider, None)


@pytest.fixture
def scenario_id(client):
    return client.get("/scenarios").json()[0]["id"]


# --------------------------------------------------------------------
# Conversation creation
# --------------------------------------------------------------------


def test_start_conversation_with_valid_scenario_creates_conversation(client, scenario_id):
    response = client.post("/conversations", json={"scenario_id": scenario_id})
    assert response.status_code == 201

    body = response.json()
    assert body["scenario_id"] == scenario_id
    assert body["status"] == "in_progress"
    assert body["end_reason"] is None
    assert body["turn_count"] == 0
    assert body["max_turns"] == 12
    assert body["messages"] == []


def test_start_conversation_with_invalid_scenario_returns_404(client):
    response = client.post("/conversations", json={"scenario_id": "does-not-exist"})
    assert response.status_code == 404


def test_start_conversation_initial_state_persisted_and_matches_persona_base_state(client, scenario_id):
    response = client.post("/conversations", json={"scenario_id": scenario_id})
    conversation_id = response.json()["id"]

    db = SessionLocal()
    try:
        from app.db.models import Conversation

        conversation = db.get(Conversation, conversation_id)
        assert conversation.current_buyer_state == _PERSONA_BASE_STATE
    finally:
        db.close()


def test_start_conversation_starts_active(client, scenario_id):
    response = client.post("/conversations", json={"scenario_id": scenario_id})
    assert response.json()["status"] == "in_progress"


# --------------------------------------------------------------------
# Conversation retrieval
# --------------------------------------------------------------------


def test_get_conversation_returns_public_information(client, scenario_id):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]

    response = client.get(f"/conversations/{conversation_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == conversation_id
    assert "messages" in body


def test_get_unknown_conversation_returns_404(client):
    response = client.get("/conversations/does-not-exist")
    assert response.status_code == 404


def test_get_conversation_never_exposes_hidden_buyer_state(client, scenario_id):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    body = client.get(f"/conversations/{conversation_id}").json()

    serialized = json.dumps(body)
    for field in ("trust", "patience", "budget_sensitivity", "interest", "current_buyer_state"):
        assert field not in serialized


# --------------------------------------------------------------------
# Turn submission
# --------------------------------------------------------------------


def test_submit_turn_creates_turn_and_returns_buyer_reply(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    mock_provider.responses = _turn_response(
        "addresses_objection_directly", "Alright, that clarifies the ROI picture."
    )

    response = client.post(f"/conversations/{conversation_id}/turns", json={"message": "Here's the ROI math..."})
    assert response.status_code == 200

    body = response.json()
    assert body["turn_count"] == 1
    assert len(body["messages"]) == 2
    assert body["messages"][0]["sender"] == "rep"
    assert body["messages"][0]["content"] == "Here's the ROI math..."
    assert body["messages"][1]["sender"] == "buyer"
    assert body["messages"][1]["content"] == "Alright, that clarifies the ROI picture."


def test_submit_turn_rep_and_buyer_messages_persisted(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    mock_provider.responses = _turn_response("rapport_building", "Nice to meet you too.")
    client.post(f"/conversations/{conversation_id}/turns", json={"message": "Great to connect!"})

    refetched = client.get(f"/conversations/{conversation_id}").json()
    assert len(refetched["messages"]) == 2


def test_submit_turn_increments_turn_count_across_multiple_turns(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]

    mock_provider.responses = _turn_response("discovery_question", "Sure, ask away.")
    r1 = client.post(f"/conversations/{conversation_id}/turns", json={"message": "What matters most to you?"})
    assert r1.json()["turn_count"] == 1

    mock_provider.responses = _turn_response("value_articulation", "That does sound useful.")
    r2 = client.post(f"/conversations/{conversation_id}/turns", json={"message": "Here's the value prop..."})
    assert r2.json()["turn_count"] == 2


def test_submit_turn_hidden_state_is_updated_in_db(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    mock_provider.responses = _turn_response(
        "addresses_objection_directly", "That helps."
    )
    client.post(f"/conversations/{conversation_id}/turns", json={"message": "..."})

    db = SessionLocal()
    try:
        from app.db.models import Conversation

        conversation = db.get(Conversation, conversation_id)
        delta = get_delta_for(RepBehavior.ADDRESSES_OBJECTION_DIRECTLY)
        assert conversation.current_buyer_state["trust"] == _PERSONA_BASE_STATE["trust"] + delta.trust
        assert (
            conversation.current_buyer_state["budget_sensitivity"]
            == _PERSONA_BASE_STATE["budget_sensitivity"] + delta.budget_sensitivity
        )
    finally:
        db.close()


def test_submit_turn_to_unknown_conversation_returns_404(client, mock_provider):
    mock_provider.responses = _turn_response("unclear", "...")
    response = client.post("/conversations/does-not-exist/turns", json={"message": "hi"})
    assert response.status_code == 404


# --------------------------------------------------------------------
# Multi-turn persistence (critical)
# --------------------------------------------------------------------


def test_turn_two_uses_turn_ones_persisted_state_not_the_initial_state(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]

    mock_provider.responses = _turn_response("addresses_objection_directly", "Reply 1")
    client.post(f"/conversations/{conversation_id}/turns", json={"message": "msg 1"})

    mock_provider.responses = _turn_response("rapport_building", "Reply 2")
    client.post(f"/conversations/{conversation_id}/turns", json={"message": "msg 2"})

    delta1 = get_delta_for(RepBehavior.ADDRESSES_OBJECTION_DIRECTLY)
    delta2 = get_delta_for(RepBehavior.RAPPORT_BUILDING)

    expected_after_turn_2 = {
        "trust": _PERSONA_BASE_STATE["trust"] + delta1.trust + delta2.trust,
        "patience": _PERSONA_BASE_STATE["patience"] + delta1.patience + delta2.patience,
        "budget_sensitivity": (
            _PERSONA_BASE_STATE["budget_sensitivity"] + delta1.budget_sensitivity + delta2.budget_sensitivity
        ),
        "interest": _PERSONA_BASE_STATE["interest"] + delta1.interest + delta2.interest,
    }
    # What it would incorrectly be if turn 2 reset to the initial state
    # instead of building on turn 1's persisted state:
    reset_to_initial = {
        "trust": _PERSONA_BASE_STATE["trust"] + delta2.trust,
        "patience": _PERSONA_BASE_STATE["patience"] + delta2.patience,
        "budget_sensitivity": _PERSONA_BASE_STATE["budget_sensitivity"] + delta2.budget_sensitivity,
        "interest": _PERSONA_BASE_STATE["interest"] + delta2.interest,
    }
    assert expected_after_turn_2 != reset_to_initial  # sanity: the two hypotheses are actually distinguishable

    db = SessionLocal()
    try:
        from app.db.models import Conversation

        conversation = db.get(Conversation, conversation_id)
        assert conversation.current_buyer_state == expected_after_turn_2
        assert conversation.current_buyer_state != reset_to_initial
    finally:
        db.close()


def test_buyer_state_history_rows_are_cumulative_across_turns(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]

    mock_provider.responses = _turn_response("addresses_objection_directly", "Reply 1")
    client.post(f"/conversations/{conversation_id}/turns", json={"message": "msg 1"})
    mock_provider.responses = _turn_response("rapport_building", "Reply 2")
    client.post(f"/conversations/{conversation_id}/turns", json={"message": "msg 2"})

    db = SessionLocal()
    try:
        rows = (
            db.query(BuyerStateHistory)
            .filter(BuyerStateHistory.conversation_id == conversation_id)
            .order_by(BuyerStateHistory.turn_index)
            .all()
        )
        assert [r.turn_index for r in rows] == [1, 2]
        assert rows[0].state["trust"] == 50  # 45 + 5 (addresses_objection_directly)
        assert rows[1].state["trust"] == 52  # 50 + 2 (rapport_building), built on turn 1
    finally:
        db.close()


# --------------------------------------------------------------------
# History
# --------------------------------------------------------------------


def test_message_history_is_correctly_ordered_with_no_duplication(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]

    mock_provider.responses = _turn_response("discovery_question", "Reply 1")
    client.post(f"/conversations/{conversation_id}/turns", json={"message": "msg 1"})
    mock_provider.responses = _turn_response("discovery_question", "Reply 2")
    client.post(f"/conversations/{conversation_id}/turns", json={"message": "msg 2"})

    body = client.get(f"/conversations/{conversation_id}").json()
    assert len(body["messages"]) == 4
    contents = [m["content"] for m in body["messages"]]
    assert contents == ["msg 1", "Reply 1", "msg 2", "Reply 2"]
    turn_indices = [m["turn_index"] for m in body["messages"]]
    assert turn_indices == sorted(turn_indices)
    assert len(set(turn_indices)) == len(turn_indices)  # no duplicates


# --------------------------------------------------------------------
# Terminal conditions
# --------------------------------------------------------------------


def test_conversation_completes_at_max_turns(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    max_turns = client.get(f"/conversations/{conversation_id}").json()["max_turns"]

    body = None
    for i in range(max_turns):
        mock_provider.responses = _turn_response("discovery_question", f"Reply {i}")
        body = client.post(f"/conversations/{conversation_id}/turns", json={"message": f"msg {i}"}).json()

    assert body["turn_count"] == max_turns
    assert body["status"] == "completed"
    assert body["end_reason"] == "turn_limit"


def test_terminal_conversation_rejects_further_turns(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    client.post(f"/conversations/{conversation_id}/close")

    mock_provider.responses = _turn_response("discovery_question", "should not be used")
    response = client.post(f"/conversations/{conversation_id}/turns", json={"message": "one more?"})
    assert response.status_code == 409


def test_terminal_conversation_does_not_mutate_state_or_append_messages(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    mock_provider.responses = _turn_response("discovery_question", "Reply 1")
    client.post(f"/conversations/{conversation_id}/turns", json={"message": "msg 1"})

    before = client.get(f"/conversations/{conversation_id}").json()
    client.post(f"/conversations/{conversation_id}/close")

    mock_provider.responses = _turn_response("discovery_question", "should not be used")
    client.post(f"/conversations/{conversation_id}/turns", json={"message": "ignored"})

    after = client.get(f"/conversations/{conversation_id}").json()
    assert after["messages"] == before["messages"]


def test_explicit_close_sets_completed_status_and_reason(client, scenario_id):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    response = client.post(f"/conversations/{conversation_id}/close")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["end_reason"] == "explicit_close"


def test_closing_an_already_completed_conversation_is_idempotent(client, scenario_id):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    client.post(f"/conversations/{conversation_id}/close")
    response = client.post(f"/conversations/{conversation_id}/close")
    assert response.status_code == 200
    assert response.json()["end_reason"] == "explicit_close"


def test_conversation_completes_when_patience_exhausted(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    # Enterprise CFO base patience is 60. aggressive_or_pressuring costs 6
    # patience per turn (60 / 6 = 10 turns to the clamp floor), which
    # lands before the scenario's max_turns (12) — isolating the patience
    # end condition from the turn-limit end condition.
    body = None
    for i in range(12):
        mock_provider.responses = _turn_response("aggressive_or_pressuring", f"Reply {i}")
        body = client.post(f"/conversations/{conversation_id}/turns", json={"message": f"msg {i}"}).json()
        if body["status"] == "completed":
            break

    assert body["status"] == "completed"
    assert body["end_reason"] == "patience_exhausted"
    assert body["turn_count"] < 12  # ended before hitting the turn limit


# --------------------------------------------------------------------
# Hidden-state protection
# --------------------------------------------------------------------


def test_turn_response_never_exposes_hidden_state_fields(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    mock_provider.responses = _turn_response("addresses_objection_directly", "That helps.")
    response = client.post(f"/conversations/{conversation_id}/turns", json={"message": "..."})

    serialized = json.dumps(response.json())
    for field in ("trust", "patience", "budget_sensitivity", "interest", "current_buyer_state", "classified_intent"):
        assert field not in serialized


def test_turn_response_never_exposes_system_prompt_or_internal_reasoning(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    mock_provider.responses = _turn_response("addresses_objection_directly", "That helps.")
    response = client.post(f"/conversations/{conversation_id}/turns", json={"message": "..."})

    serialized = json.dumps(response.json()).lower()
    for phrase in ("system prompt", "rationale", "classification"):
        assert phrase not in serialized


# --------------------------------------------------------------------
# Failure behavior
# --------------------------------------------------------------------


def test_submit_turn_degrades_gracefully_when_llm_unavailable(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    mock_provider.always_fail = True

    response = client.post(f"/conversations/{conversation_id}/turns", json={"message": "hello"})
    assert response.status_code == 200
    body = response.json()
    # Phase 6's graceful degradation still produces a non-empty fallback
    # buyer reply and a real (UNCLEAR) turn — the conversation is not
    # broken, no second fallback system is invented here.
    assert body["turn_count"] == 1
    assert body["messages"][1]["content"]


def test_submit_turn_to_invalid_conversation_id_returns_404_not_500(client, mock_provider):
    mock_provider.responses = _turn_response("unclear", "...")
    response = client.post("/conversations/totally-invalid-id/turns", json={"message": "hi"})
    assert response.status_code == 404


def test_submit_turn_to_completed_conversation_returns_409_not_500(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    client.post(f"/conversations/{conversation_id}/close")

    mock_provider.responses = _turn_response("unclear", "...")
    response = client.post(f"/conversations/{conversation_id}/turns", json={"message": "hi"})
    assert response.status_code == 409


def test_empty_message_is_rejected_with_validation_error(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    response = client.post(f"/conversations/{conversation_id}/turns", json={"message": ""})
    assert response.status_code == 422
