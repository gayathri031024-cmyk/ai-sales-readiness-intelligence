"""
Phase 8 — Evidence-Based Evaluation Engine: extraction, deterministic
verification, competency scoring, persistence, API, and hidden-state /
graceful-degradation guarantees.

Same MockLLMProvider-only discipline as Phase 6/7: no real LLM_API_KEY /
ANTHROPIC_API_KEY is ever required. Both direct unit tests (against the
pure `verification.py` / deterministic `scoring.py` functions, no DB or
HTTP needed) and full API-level integration tests are included, mirroring
the project's existing mix (e.g. test_buyer_rules.py vs. test_conversation.py).
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.ai.provider import MockLLMProvider
from app.api.routes.conversation import get_llm_provider
from app.db.base import SessionLocal
from app.db.models import Evaluation, Evidence
from app.evaluation.extraction import EvidenceCandidate
from app.evaluation.scoring import no_evidence_result, score_competency, unavailable_result
from app.evaluation.verification import TranscriptMessage, verify_evidence
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


def _turn_response(behavior: str, reply: str) -> list[str]:
    return [json.dumps({"behavior": behavior, "confidence": 0.9, "rationale": "note"}), reply]


def _evidence_response(items: list[dict]) -> str:
    return json.dumps({"evidence": items})


def _score_response(score: int, diagnosis: str = "d", impact: str = "i", recommendation: str = "r") -> str:
    return json.dumps({"score": score, "diagnosis": diagnosis, "impact": impact, "recommendation": recommendation})


def _start_and_populate_conversation(client, scenario_id, mock_provider, rep_messages: list[str]) -> str:
    """Creates a conversation, submits one turn per rep message (each
    using a generic classification+reply pair so buyer-engine behavior
    doesn't interfere with evaluation-specific assertions), then closes
    it so it's eligible for evaluation. Rep messages land at turn_index
    1, 3, 5, ... per conversation/service.py's `_next_turn_indices`."""
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    for msg in rep_messages:
        mock_provider.responses = _turn_response("discovery_question", "Buyer reply.")
        client.post(f"/conversations/{conversation_id}/turns", json={"message": msg})
    client.post(f"/conversations/{conversation_id}/close")
    return conversation_id


# --------------------------------------------------------------------
# 1/9/10. Valid evidence extraction + competency scoring + multiple competencies
# --------------------------------------------------------------------


def test_valid_evidence_extraction_and_scoring_persists_correctly(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client,
        scenario_id,
        mock_provider,
        rep_messages=["What's driving your budget cycle this year?", "Let's talk about next steps."],
    )

    mock_provider.responses = [
        _evidence_response(
            [
                {
                    "turn_index": 1,
                    "competency_key": "discovery",
                    "quote": "What's driving your budget cycle this year?",
                    "note": "Open discovery question",
                },
                {
                    "turn_index": 3,
                    "competency_key": "closing",
                    "quote": "Let's talk about next steps.",
                    "note": "Moves toward a decision",
                },
            ]
        ),
        # objection_handling gets no evidence above, so it's skipped
        # deterministically (no LLM call for it) — only discovery and
        # closing consume a scoring response, in that order.
        _score_response(80, "Strong open questions.", "Builds rapport early.", "Ask about stakeholders next."),
        _score_response(70, "Clear next-step ask.", "Moves the deal forward.", "Confirm a specific date."),
    ]

    calls_before = len(mock_provider.calls)
    response = client.post(f"/conversations/{conversation_id}/evaluate")
    assert response.status_code == 200
    body = response.json()

    assert body["conversation_id"] == conversation_id
    assert len(body["evaluations"]) == 3
    by_key = {e["competency_key"]: e for e in body["evaluations"]}

    assert by_key["discovery"]["score"] == 80
    assert by_key["discovery"]["display_name"] == "Discovery"
    assert len(by_key["discovery"]["evidence"]) == 1
    assert by_key["discovery"]["evidence"][0]["quote"] == "What's driving your budget cycle this year?"
    assert by_key["discovery"]["evidence"][0]["turn_index"] == 1

    assert by_key["closing"]["score"] == 70
    assert len(by_key["closing"]["evidence"]) == 1

    # objection_handling had no evidence -> deterministic no-evidence path,
    # never called the LLM for its score (only 1 extraction + 2 scoring
    # calls were queued above, for discovery and closing).
    assert by_key["objection_handling"]["score"] == 0
    assert by_key["objection_handling"]["evidence"] == []
    assert len(mock_provider.calls) - calls_before == 3  # 1 extraction + 2 scoring (not 3)


# --------------------------------------------------------------------
# 6/7. Evidence grounded in transcript / hallucination rejection (unit-level)
# --------------------------------------------------------------------


def _messages() -> list[TranscriptMessage]:
    return [
        TranscriptMessage(id="m1", turn_index=1, sender="rep", content="What matters most to you this year?"),
        TranscriptMessage(id="m2", turn_index=2, sender="buyer", content="Price is a big concern for us."),
        TranscriptMessage(id="m3", turn_index=3, sender="rep", content="I hear you on price, let's dig into ROI."),
    ]


def test_verify_evidence_accepts_a_grounded_rep_quote():
    candidates = [
        EvidenceCandidate(turn_index=1, competency_key="discovery", quote="What matters most to you this year?")
    ]
    verified = verify_evidence(candidates, _messages())
    assert len(verified) == 1
    assert verified[0].message_id == "m1"
    assert verified[0].quote == "What matters most to you this year?"


def test_verify_evidence_rejects_quote_never_actually_said():
    candidates = [
        EvidenceCandidate(
            turn_index=1, competency_key="discovery", quote="I guarantee this will double your revenue"
        )
    ]
    assert verify_evidence(candidates, _messages()) == []


def test_verify_evidence_rejects_reference_to_nonexistent_turn():
    candidates = [EvidenceCandidate(turn_index=99, competency_key="discovery", quote="anything")]
    assert verify_evidence(candidates, _messages()) == []


def test_verify_evidence_rejects_quote_attributed_to_buyer_message():
    # turn 2 is the BUYER line "Price is a big concern for us." — even
    # though those exact words exist in the transcript, evidence of the
    # REP's competency can never be grounded in what the buyer said.
    candidates = [
        EvidenceCandidate(turn_index=2, competency_key="objection_handling", quote="Price is a big concern for us.")
    ]
    assert verify_evidence(candidates, _messages()) == []


def test_verify_evidence_is_whitespace_and_case_tolerant():
    candidates = [
        EvidenceCandidate(turn_index=1, competency_key="discovery", quote="what MATTERS most   to you this year?")
    ]
    verified = verify_evidence(candidates, _messages())
    assert len(verified) == 1


def test_hallucinated_evidence_never_reaches_the_api_response(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["Tell me about your current setup."]
    )

    mock_provider.responses = [
        _evidence_response(
            [
                {
                    "turn_index": 1,
                    "competency_key": "discovery",
                    "quote": "Tell me about your current setup.",
                    "note": "real",
                },
                {
                    # Hallucinated: this was never said by the rep.
                    "turn_index": 1,
                    "competency_key": "closing",
                    "quote": "I can guarantee you 50% savings today only",
                    "note": "fabricated",
                },
            ]
        ),
        _score_response(65, "Asked about current setup.", "Establishes context.", "Follow with a pain question."),
    ]

    response = client.post(f"/conversations/{conversation_id}/evaluate")
    body = response.json()
    serialized = json.dumps(body)
    assert "guarantee" not in serialized
    assert "50% savings" not in serialized

    by_key = {e["competency_key"]: e for e in body["evaluations"]}
    # closing got no valid evidence, so it took the deterministic
    # no-evidence path and the LLM was never asked to score it (only 1
    # extraction + 1 scoring call were queued above).
    assert by_key["closing"]["score"] == 0
    assert by_key["closing"]["evidence"] == []


# --------------------------------------------------------------------
# 2/3/4. Evidence schema validation / malformed output / structured retry
# --------------------------------------------------------------------


def test_extraction_retries_once_on_malformed_json_then_succeeds(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["What's your timeline?"]
    )

    mock_provider.responses = [
        "not valid json at all",  # first attempt fails -> call_structured retries once
        _evidence_response(
            [{"turn_index": 1, "competency_key": "discovery", "quote": "What's your timeline?", "note": None}]
        ),
        _score_response(60),
    ]

    response = client.post(f"/conversations/{conversation_id}/evaluate")
    assert response.status_code == 200
    by_key = {e["competency_key"]: e for e in response.json()["evaluations"]}
    assert by_key["discovery"]["score"] == 60
    assert len(by_key["discovery"]["evidence"]) == 1


def test_extraction_rejects_evidence_with_invalid_competency_key(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["What's your timeline?"]
    )

    mock_provider.responses = [
        # "budget" is not one of the 3 fixed MVP competency keys -> fails
        # EvidenceCandidate's Literal validation -> call_structured retries
        # once with the validation error, then this valid response succeeds.
        json.dumps({"evidence": [{"turn_index": 1, "competency_key": "budget", "quote": "x"}]}),
        _evidence_response([]),
    ]

    calls_before = len(mock_provider.calls)
    response = client.post(f"/conversations/{conversation_id}/evaluate")
    assert response.status_code == 200
    # No valid evidence for any competency -> all 3 deterministic, no
    # further LLM calls (2 extraction attempts, 0 scoring calls).
    assert len(mock_provider.calls) - calls_before == 2
    for e in response.json()["evaluations"]:
        assert e["score"] == 0
        assert e["evidence"] == []


# --------------------------------------------------------------------
# 5. Complete LLM failure (extraction stage)
# --------------------------------------------------------------------


def test_evaluation_degrades_gracefully_when_llm_completely_unavailable(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["Here's what we can offer."]
    )
    mock_provider.always_fail = True

    response = client.post(f"/conversations/{conversation_id}/evaluate")
    assert response.status_code == 200
    body = response.json()
    assert len(body["evaluations"]) == 3
    for e in body["evaluations"]:
        assert e["score"] == 0
        assert e["evidence"] == []
        assert e["diagnosis"]  # non-empty, safe fallback text present


def test_scoring_degrades_gracefully_when_llm_fails_after_extraction_succeeds(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["What's your timeline?"]
    )
    mock_provider.responses = [
        _evidence_response(
            [{"turn_index": 1, "competency_key": "discovery", "quote": "What's your timeline?", "note": None}]
        )
    ]
    # After the queued extraction response is consumed, force every
    # subsequent call (the scoring call for discovery) to fail.
    original_complete = mock_provider.complete

    def _fail_after_first(*, system, user, max_tokens=1000):
        if not mock_provider.responses:
            from app.ai.provider import LLMUnavailableError

            mock_provider.calls.append({"system": system, "user": user, "max_tokens": max_tokens})
            raise LLMUnavailableError("simulated scoring outage")
        return original_complete(system=system, user=user, max_tokens=max_tokens)

    mock_provider.complete = _fail_after_first

    response = client.post(f"/conversations/{conversation_id}/evaluate")
    assert response.status_code == 200
    by_key = {e["competency_key"]: e for e in response.json()["evaluations"]}
    # Evidence WAS found and verified, but scoring failed — this must read
    # differently from "no evidence observed" (score 0, empty evidence).
    assert by_key["discovery"]["score"] == 0
    assert len(by_key["discovery"]["evidence"]) == 1  # evidence still persisted
    assert "unavailable" in by_key["discovery"]["diagnosis"].lower()


# --------------------------------------------------------------------
# 8/11. Evidence + evaluation persistence (DB-level)
# --------------------------------------------------------------------


def test_evaluation_and_evidence_rows_are_persisted_in_db(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["What's your timeline?"]
    )
    mock_provider.responses = [
        _evidence_response(
            [{"turn_index": 1, "competency_key": "discovery", "quote": "What's your timeline?", "note": "n"}]
        ),
        _score_response(55),
    ]
    client.post(f"/conversations/{conversation_id}/evaluate")

    db = SessionLocal()
    try:
        evaluations = db.query(Evaluation).filter(Evaluation.conversation_id == conversation_id).all()
        assert len(evaluations) == 3  # one row per MVP competency, always

        discovery_eval = next(e for e in evaluations if e.competency.key == "discovery")
        assert discovery_eval.score == 55

        evidence_rows = db.query(Evidence).filter(Evidence.evaluation_id == discovery_eval.id).all()
        assert len(evidence_rows) == 1
        assert evidence_rows[0].quote == "What's your timeline?"
        assert evidence_rows[0].message.turn_index == 1
        assert evidence_rows[0].message.sender == "rep"
    finally:
        db.close()


# --------------------------------------------------------------------
# 12. Evaluation retrieval
# --------------------------------------------------------------------


def test_get_evaluation_returns_previously_persisted_result(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["What's your timeline?"]
    )
    mock_provider.responses = [_evidence_response([]), ]
    post_body = client.post(f"/conversations/{conversation_id}/evaluate").json()

    get_response = client.get(f"/conversations/{conversation_id}/evaluation")
    assert get_response.status_code == 200
    assert get_response.json() == post_body


def test_get_evaluation_404_when_not_yet_evaluated(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["Hi there."]
    )
    response = client.get(f"/conversations/{conversation_id}/evaluation")
    assert response.status_code == 404


def test_get_evaluation_404_for_unknown_conversation(client):
    response = client.get("/conversations/does-not-exist/evaluation")
    assert response.status_code == 404


# --------------------------------------------------------------------
# 13. Duplicate / idempotent evaluation behavior
# --------------------------------------------------------------------


def test_evaluate_is_idempotent_no_duplicate_rows_or_repeat_llm_calls(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["What's your timeline?"]
    )
    mock_provider.responses = [
        _evidence_response(
            [{"turn_index": 1, "competency_key": "discovery", "quote": "What's your timeline?", "note": None}]
        ),
        _score_response(60),
    ]
    first = client.post(f"/conversations/{conversation_id}/evaluate").json()
    calls_after_first = len(mock_provider.calls)

    # No new responses queued — if a second LLM call were made it would
    # fall through to the empty default_response ("{}") and fail schema
    # validation, surfacing as a very different (degraded) result.
    second = client.post(f"/conversations/{conversation_id}/evaluate").json()

    assert first == second
    assert len(mock_provider.calls) == calls_after_first  # no new calls made

    db = SessionLocal()
    try:
        evaluations = db.query(Evaluation).filter(Evaluation.conversation_id == conversation_id).all()
        assert len(evaluations) == 3  # still exactly 3, not 6
    finally:
        db.close()


# --------------------------------------------------------------------
# 14/15/16. Hidden-state / system-prompt / internal-reasoning protection
# --------------------------------------------------------------------


def test_evaluation_response_never_exposes_hidden_buyer_state(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["What's your timeline?"]
    )
    mock_provider.responses = [
        _evidence_response(
            [{"turn_index": 1, "competency_key": "discovery", "quote": "What's your timeline?", "note": None}]
        ),
        _score_response(60),
    ]
    response = client.post(f"/conversations/{conversation_id}/evaluate")
    serialized = json.dumps(response.json())
    for field in ("trust", "patience", "budget_sensitivity", "interest", "current_buyer_state"):
        assert field not in serialized


def test_evaluation_response_never_exposes_system_prompt_or_internal_reasoning(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["What's your timeline?"]
    )
    mock_provider.responses = [
        _evidence_response(
            [{"turn_index": 1, "competency_key": "discovery", "quote": "What's your timeline?", "note": None}]
        ),
        _score_response(60),
    ]
    response = client.post(f"/conversations/{conversation_id}/evaluate")
    serialized = json.dumps(response.json()).lower()
    for phrase in ("system prompt", "internal reasoning", "chain of thought", "classified_intent"):
        assert phrase not in serialized


def test_scoring_scrubber_catches_a_leak_shaped_result():
    from app.evaluation.scoring import CompetencyScoreResult, _looks_like_leak

    result = CompetencyScoreResult(
        score=50, diagnosis="my trust is 80", impact="fine", recommendation="none"
    )
    assert _looks_like_leak(result) is True


# --------------------------------------------------------------------
# 17. Public API response schema
# --------------------------------------------------------------------


def test_evaluation_response_schema_has_expected_fields(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client, scenario_id, mock_provider, rep_messages=["What's your timeline?"]
    )
    mock_provider.responses = [
        _evidence_response(
            [{"turn_index": 1, "competency_key": "discovery", "quote": "What's your timeline?", "note": "n"}]
        ),
        _score_response(60),
    ]
    body = client.post(f"/conversations/{conversation_id}/evaluate").json()

    assert set(body.keys()) == {"conversation_id", "evaluations"}
    evaluation = body["evaluations"][0]
    assert set(evaluation.keys()) == {
        "id",
        "competency_key",
        "display_name",
        "score",
        "diagnosis",
        "impact",
        "recommendation",
        "created_at",
        "evidence",
    }
    evidence = next(e for e in body["evaluations"] if e["competency_key"] == "discovery")["evidence"][0]
    assert set(evidence.keys()) == {"id", "message_id", "turn_index", "quote", "note"}


# --------------------------------------------------------------------
# 18. API error handling
# --------------------------------------------------------------------


def test_evaluate_unknown_conversation_returns_404(client):
    response = client.post("/conversations/does-not-exist/evaluate")
    assert response.status_code == 404


def test_evaluate_in_progress_conversation_returns_409(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    # Never closed — still in_progress.
    response = client.post(f"/conversations/{conversation_id}/evaluate")
    assert response.status_code == 409


# --------------------------------------------------------------------
# 19. Empty / short conversation behavior
# --------------------------------------------------------------------


def test_evaluate_conversation_with_zero_turns_is_fully_deterministic_no_llm_call(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    client.post(f"/conversations/{conversation_id}/close")  # closed with zero turns

    response = client.post(f"/conversations/{conversation_id}/evaluate")
    assert response.status_code == 200
    body = response.json()
    assert len(body["evaluations"]) == 3
    for e in body["evaluations"]:
        assert e["score"] == 0
        assert e["evidence"] == []
    assert mock_provider.calls == []  # no LLM call at all for an empty transcript


# --------------------------------------------------------------------
# 20. MockLLMProvider behavior (extraction/scoring call ordering)
# --------------------------------------------------------------------


def test_extraction_and_scoring_call_order_matches_competency_order(client, scenario_id, mock_provider):
    conversation_id = _start_and_populate_conversation(
        client,
        scenario_id,
        mock_provider,
        rep_messages=["Discovery question here.", "Handling the objection now.", "Asking for the close."],
    )
    mock_provider.responses = [
        _evidence_response(
            [
                {"turn_index": 1, "competency_key": "discovery", "quote": "Discovery question here."},
                {"turn_index": 3, "competency_key": "objection_handling", "quote": "Handling the objection now."},
                {"turn_index": 5, "competency_key": "closing", "quote": "Asking for the close."},
            ]
        ),
        _score_response(10),  # discovery
        _score_response(20),  # objection_handling
        _score_response(30),  # closing
    ]
    calls_before = len(mock_provider.calls)
    response = client.post(f"/conversations/{conversation_id}/evaluate")
    by_key = {e["competency_key"]: e for e in response.json()["evaluations"]}
    assert by_key["discovery"]["score"] == 10
    assert by_key["objection_handling"]["score"] == 20
    assert by_key["closing"]["score"] == 30
    assert len(mock_provider.calls) - calls_before == 4  # 1 extraction + 3 scoring


# --------------------------------------------------------------------
# Deterministic scoring fallback unit tests
# --------------------------------------------------------------------


def test_no_evidence_result_is_deterministic_and_distinct_from_unavailable_result():
    no_ev = no_evidence_result("discovery")
    unavailable = unavailable_result("discovery")
    assert no_ev.score == 0
    assert unavailable.score == 0
    assert no_ev.diagnosis != unavailable.diagnosis  # distinguishable to a human reader


def test_score_competency_skips_llm_entirely_when_no_evidence():
    provider = MockLLMProvider()
    result, degraded = score_competency(provider, "closing", [])
    assert degraded is False
    assert result.score == 0
    assert provider.calls == []


# --------------------------------------------------------------------
# 21. Regression — Phase 0-7 tests still pass alongside these (see
# TEST_STATUS.md; verified by running the full suite together, not
# re-implemented here).
# --------------------------------------------------------------------
