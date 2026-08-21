"""
Phase 14 — Skill Graph: a small, static, hand-authored set of
"depends_on" edges between the MVP's 3 competencies (discovery,
objection_handling, closing), used to deterministically (zero-LLM)
surface evidence-hedged, never-proven-causal correlations between
weaknesses observed in the same conversation.

Mirrors test_difficulty.py's organization (the other zero-LLM,
read-only-endpoint module): pure unit-level tests for `analysis.py`,
a seed-idempotency test, and full API-level tests for the endpoint.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.ai.provider import MockLLMProvider
from app.api.routes.conversation import get_llm_provider
from app.db.base import SessionLocal
from app.db.models import Competency, SkillGraphEdge
from app.main import app
from app.readiness.decision import CompetencyResult
from app.skill_graph.analysis import RelatedWeakness, SkillGraphEdgeInfo, find_related_weaknesses
from app.skill_graph.seed import seed_mvp_skill_graph

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


def _start_and_evaluate(client, scenario_id, mock_provider, scores: dict[str, int]) -> str:
    """Creates a conversation, submits one rep turn per MVP competency,
    closes it, evaluates with the given exact scores — everything
    Phase 14's root-cause analysis requires as a precondition (no
    readiness computation needed, unlike Phase 12's difficulty
    endpoint). `scores` keys: "discovery", "objection_handling",
    "closing"."""
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
    return conversation_id


_DISPLAY_NAMES = {"discovery": "Discovery", "objection_handling": "Objection Handling", "closing": "Closing"}


def _result(key: str, score: int, min_score: int) -> CompetencyResult:
    return CompetencyResult(competency_key=key, display_name=_DISPLAY_NAMES[key], score=score, min_score=min_score)


_MVP_EDGES = [
    SkillGraphEdgeInfo(from_competency_key="closing", to_competency_key="discovery"),
    SkillGraphEdgeInfo(from_competency_key="closing", to_competency_key="objection_handling"),
    SkillGraphEdgeInfo(from_competency_key="objection_handling", to_competency_key="discovery"),
]


# --------------------------------------------------------------------
# Unit-level: find_related_weaknesses (pure function, no DB/HTTP/LLM)
# --------------------------------------------------------------------


def test_no_failing_competencies_returns_empty():
    results = [_result("discovery", 90, 60), _result("objection_handling", 90, 70), _result("closing", 90, 65)]
    diagnoses = {"discovery": "d1", "objection_handling": "d2", "closing": "d3"}
    assert find_related_weaknesses(results, diagnoses, _MVP_EDGES) == {}


def test_failing_competency_with_no_edges_is_absent():
    # discovery has no outgoing edges in the MVP graph
    results = [_result("discovery", 10, 60), _result("objection_handling", 90, 70), _result("closing", 90, 65)]
    diagnoses = {"discovery": "d1", "objection_handling": "d2", "closing": "d3"}
    related = find_related_weaknesses(results, diagnoses, _MVP_EDGES)
    assert "discovery" not in related


def test_failing_competency_with_only_passing_upstream_is_absent():
    # closing fails but both discovery and objection_handling pass
    results = [_result("discovery", 90, 60), _result("objection_handling", 90, 70), _result("closing", 10, 65)]
    diagnoses = {"discovery": "d1", "objection_handling": "d2", "closing": "d3"}
    related = find_related_weaknesses(results, diagnoses, _MVP_EDGES)
    assert related == {}


def test_failing_competency_with_failing_upstream_is_included_with_hedged_reason():
    results = [_result("discovery", 10, 60), _result("objection_handling", 90, 70), _result("closing", 10, 65)]
    diagnoses = {"discovery": "Rep skipped discovery questions.", "objection_handling": "d2", "closing": "d3"}
    related = find_related_weaknesses(results, diagnoses, _MVP_EDGES)
    assert "closing" in related
    assert len(related["closing"]) == 1
    weakness = related["closing"][0]
    assert weakness.competency_key == "discovery"
    assert "may be a contributing factor" in weakness.reason
    assert "Rep skipped discovery questions." in weakness.reason
    # never a strict causal claim
    assert "caused by" not in weakness.reason.lower()
    assert "is the root cause" not in weakness.reason.lower()


def test_multiple_failing_upstream_dependencies_all_included():
    results = [_result("discovery", 10, 60), _result("objection_handling", 10, 70), _result("closing", 10, 65)]
    diagnoses = {"discovery": "d1", "objection_handling": "d2", "closing": "d3"}
    related = find_related_weaknesses(results, diagnoses, _MVP_EDGES)
    closing_keys = {w.competency_key for w in related["closing"]}
    assert closing_keys == {"discovery", "objection_handling"}
    # objection_handling itself depends on discovery, also failing
    assert "objection_handling" in related
    assert related["objection_handling"][0].competency_key == "discovery"


def test_missing_diagnosis_for_upstream_excludes_it():
    results = [_result("discovery", 10, 60), _result("closing", 10, 65)]
    diagnoses = {"closing": "d3"}  # no diagnosis recorded for discovery
    edges = [SkillGraphEdgeInfo(from_competency_key="closing", to_competency_key="discovery")]
    related = find_related_weaknesses(results, diagnoses, edges)
    assert related == {}


def test_edge_referencing_unknown_competency_does_not_crash():
    results = [_result("closing", 10, 65)]
    diagnoses = {"closing": "d3"}
    edges = [SkillGraphEdgeInfo(from_competency_key="closing", to_competency_key="negotiation")]
    related = find_related_weaknesses(results, diagnoses, edges)
    assert related == {}


def test_related_weakness_is_a_frozen_dataclass_instance():
    results = [_result("discovery", 10, 60), _result("closing", 10, 65)]
    diagnoses = {"discovery": "d1", "closing": "d3"}
    edges = [SkillGraphEdgeInfo(from_competency_key="closing", to_competency_key="discovery")]
    related = find_related_weaknesses(results, diagnoses, edges)
    assert isinstance(related["closing"][0], RelatedWeakness)


# --------------------------------------------------------------------
# Seed idempotency (DB, no HTTP, no LLM)
# --------------------------------------------------------------------


def test_seed_mvp_skill_graph_is_idempotent(client):
    db = SessionLocal()
    try:
        seed_mvp_skill_graph(db)
        seed_mvp_skill_graph(db)
        edges = db.query(SkillGraphEdge).all()
        assert len(edges) == 3
    finally:
        db.close()


def test_seeded_edges_reference_real_competency_rows(client):
    db = SessionLocal()
    try:
        seed_mvp_skill_graph(db)
        edges = db.query(SkillGraphEdge).all()
        competency_ids = {c.id for c in db.query(Competency).all()}
        for edge in edges:
            assert edge.from_competency_id in competency_ids
            assert edge.to_competency_id in competency_ids
            assert edge.relationship_type == "depends_on"
    finally:
        db.close()


# --------------------------------------------------------------------
# API-level: GET /conversations/{id}/root-cause-analysis
# --------------------------------------------------------------------


def test_root_cause_analysis_before_evaluation_returns_409(client, scenario_id, mock_provider):
    conversation_id = client.post("/conversations", json={"scenario_id": scenario_id}).json()["id"]
    resp = client.get(f"/conversations/{conversation_id}/root-cause-analysis")
    assert resp.status_code == 409


def test_root_cause_analysis_404_for_unknown_conversation(client):
    resp = client.get("/conversations/does-not-exist/root-cause-analysis")
    assert resp.status_code == 404


def test_root_cause_analysis_surfaces_closing_related_to_discovery(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider,
        {"discovery": 20, "objection_handling": 85, "closing": 30},
    )
    resp = client.get(f"/conversations/{conversation_id}/root-cause-analysis")
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation_id"] == conversation_id
    keys = {rc["competency_key"] for rc in body["root_causes"]}
    assert keys == {"closing"}
    closing_entry = next(rc for rc in body["root_causes"] if rc["competency_key"] == "closing")
    related_keys = {w["competency_key"] for w in closing_entry["related_weaknesses"]}
    assert related_keys == {"discovery"}
    assert "may be a contributing factor" in closing_entry["related_weaknesses"][0]["reason"]


def test_root_cause_analysis_omits_a_failing_competency_with_no_failing_upstream(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider,
        {"discovery": 90, "objection_handling": 90, "closing": 20},
    )
    resp = client.get(f"/conversations/{conversation_id}/root-cause-analysis")
    assert resp.status_code == 200
    assert resp.json()["root_causes"] == []


def test_root_cause_analysis_multi_level_when_everything_fails(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider,
        {"discovery": 10, "objection_handling": 10, "closing": 10},
    )
    resp = client.get(f"/conversations/{conversation_id}/root-cause-analysis")
    body = resp.json()
    by_key = {rc["competency_key"]: rc for rc in body["root_causes"]}
    assert set(by_key.keys()) == {"closing", "objection_handling"}
    assert {w["competency_key"] for w in by_key["closing"]["related_weaknesses"]} == {
        "discovery",
        "objection_handling",
    }
    assert {w["competency_key"] for w in by_key["objection_handling"]["related_weaknesses"]} == {"discovery"}


def test_root_cause_analysis_makes_zero_llm_calls(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider,
        {"discovery": 10, "objection_handling": 85, "closing": 10},
    )
    calls_before = len(mock_provider.calls)
    client.get(f"/conversations/{conversation_id}/root-cause-analysis")
    assert len(mock_provider.calls) == calls_before


def test_root_cause_analysis_identical_across_repeated_calls(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider,
        {"discovery": 10, "objection_handling": 85, "closing": 10},
    )
    first = client.get(f"/conversations/{conversation_id}/root-cause-analysis").json()
    second = client.get(f"/conversations/{conversation_id}/root-cause-analysis").json()
    assert first == second


def test_root_cause_analysis_response_never_exposes_hidden_buyer_state(client, scenario_id, mock_provider):
    conversation_id = _start_and_evaluate(
        client, scenario_id, mock_provider,
        {"discovery": 10, "objection_handling": 85, "closing": 10},
    )
    resp = client.get(f"/conversations/{conversation_id}/root-cause-analysis")
    body_text = json.dumps(resp.json())
    assert "current_buyer_state" not in body_text
    assert "trust" not in body_text and "patience" not in body_text and "budget_sensitivity" not in body_text
