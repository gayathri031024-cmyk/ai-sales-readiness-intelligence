"""
Regression guard (Phase 6 required test #12): hidden buyer state must
never appear in anything the buyer module hands back for a rep/frontend
to see — only in the parts of the result explicitly meant for internal
persistence.

Complements tests/test_scenario.py::test_buyer_hidden_state_never_appears_in_scenario_responses,
which covers the Phase 5 scenario API surface. This covers the new
Phase 6 buyer-turn surface: BuyerTurnResult.buyer_reply specifically —
the one field of the result a future Phase 7 API route would actually
forward to the frontend.
"""
import json

from app.ai.provider import MockLLMProvider
from app.buyer.service import run_buyer_turn
from app.buyer.state import BuyerState

_BASE = dict(
    current_state=BuyerState(trust=37, patience=82, budget_sensitivity=61, interest=44),
    persona_name="Enterprise CFO",
    persona_description="High sophistication buyer.",
    product_context="AI CRM platform",
    known_objection="Price",
)


def test_buyer_reply_text_never_contains_any_state_field_name():
    provider = MockLLMProvider(
        responses=[
            json.dumps({"behavior": "discovery_question", "confidence": 0.8, "rationale": "n/a"}),
            "That's a fair question — let's discuss what matters most to my team this quarter.",
        ]
    )
    result = run_buyer_turn(provider, rep_message="What matters most to you?", **_BASE)
    for field_name in ("trust", "patience", "budget_sensitivity", "interest"):
        assert field_name not in result.buyer_reply.lower()


def test_buyer_reply_never_contains_the_exact_seeded_numeric_values():
    provider = MockLLMProvider(
        responses=[
            json.dumps({"behavior": "rapport_building", "confidence": 0.8, "rationale": "n/a"}),
            "Good to connect — appreciate you taking the time.",
        ]
    )
    result = run_buyer_turn(provider, rep_message="Nice to meet you.", **_BASE)
    for value in (37, 82, 61, 44):
        assert str(value) not in result.buyer_reply


def test_result_object_separates_reply_from_state_at_the_type_level():
    # Structural guarantee: BuyerTurnResult has distinct fields, so a
    # caller (e.g. a future API route) forwarding only `.buyer_reply` to
    # the frontend structurally cannot leak `.new_state` by accident —
    # they are not nested inside the same string/object.
    provider = MockLLMProvider(
        responses=[
            json.dumps({"behavior": "unclear", "confidence": 0.3, "rationale": "n/a"}),
            "Sorry, could you clarify?",
        ]
    )
    result = run_buyer_turn(provider, rep_message="???", **_BASE)
    assert isinstance(result.buyer_reply, str)
    assert isinstance(result.new_state, BuyerState)
    assert result.new_state is not result.buyer_reply
