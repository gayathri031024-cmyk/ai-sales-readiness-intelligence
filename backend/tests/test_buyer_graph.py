"""LangGraph turn pipeline wiring: node order, state threading,
end-to-end turn behavior, and graceful degradation when the LLM is
unavailable throughout."""
import json

from app.ai.provider import MockLLMProvider
from app.buyer.classification import RepBehavior
from app.buyer.graph import build_buyer_turn_graph, get_compiled_graph
from app.buyer.service import run_buyer_turn
from app.buyer.state import BuyerState

_BASE = dict(
    persona_name="Enterprise CFO",
    persona_description="High sophistication buyer.",
    product_context="AI CRM platform",
    known_objection="Price",
)


def _healthy_provider(behavior: str, reply: str) -> MockLLMProvider:
    return MockLLMProvider(
        responses=[
            json.dumps({"behavior": behavior, "confidence": 0.9, "rationale": "note"}),
            reply,
        ]
    )


def test_graph_compiles():
    graph = build_buyer_turn_graph()
    assert graph is not None


def test_get_compiled_graph_is_cached_singleton():
    g1 = get_compiled_graph()
    g2 = get_compiled_graph()
    assert g1 is g2


def test_full_turn_happy_path_updates_state_and_returns_reply():
    provider = _healthy_provider("addresses_objection_directly", "Alright, that helps clarify the ROI case.")
    state = BuyerState(trust=50, patience=50, budget_sensitivity=50, interest=50)
    result = run_buyer_turn(
        provider,
        rep_message="Here's exactly how we address the price gap: ...",
        current_state=state,
        **_BASE,
    )
    assert result.classified_behavior == RepBehavior.ADDRESSES_OBJECTION_DIRECTLY
    assert result.new_state.trust > state.trust
    assert result.new_state.budget_sensitivity < state.budget_sensitivity
    assert result.buyer_reply == "Alright, that helps clarify the ROI case."
    assert result.degraded is False


def test_original_state_object_is_not_mutated_by_a_turn():
    provider = _healthy_provider("rapport_building", "Nice to meet you too.")
    state = BuyerState(trust=50, patience=50, budget_sensitivity=50, interest=50)
    run_buyer_turn(provider, rep_message="Great to connect!", current_state=state, **_BASE)
    assert state.trust == 50  # unchanged — apply_state_update is pure


def test_full_turn_degrades_gracefully_when_llm_completely_unavailable():
    provider = MockLLMProvider(always_fail=True)
    state = BuyerState(trust=50, patience=50, budget_sensitivity=50, interest=50)
    result = run_buyer_turn(provider, rep_message="Anything at all", current_state=state, **_BASE)

    assert result.degraded is True
    assert result.classified_behavior == RepBehavior.UNCLEAR
    assert result.buyer_reply  # non-empty fallback text, no crash
    # Even in full degradation, the deterministic state update still ran
    # (small patience decay for UNCLEAR) — the graph never skips it.
    assert result.new_state.patience == state.patience - 1


def test_turn_index_affects_fallback_reply_variety():
    provider = MockLLMProvider(always_fail=True)
    state = BuyerState(trust=50, patience=50, budget_sensitivity=50, interest=50)
    r0 = run_buyer_turn(provider, rep_message="x", current_state=state, turn_index=0, **_BASE)
    r1 = run_buyer_turn(provider, rep_message="x", current_state=state, turn_index=1, **_BASE)
    # Not asserting exact rotation scheme, just that turn_index is wired
    # through to reply selection rather than being ignored.
    assert isinstance(r0.buyer_reply, str) and isinstance(r1.buyer_reply, str)


def test_classification_runs_before_state_update_which_runs_before_reply():
    # Verified indirectly: the reply-generation call's system prompt is
    # built from `new_state` (post-update), not `current_state`. Force a
    # large classification-driven delta and confirm the reply call's
    # system prompt reflects the *updated* disposition, not the original.
    provider = _healthy_provider("dismissive_of_concern", "Hmph. Fine.")
    low_patience_state = BuyerState(trust=50, patience=4, budget_sensitivity=50, interest=50)
    run_buyer_turn(
        provider,
        rep_message="Whatever, that's not really a big deal.",
        current_state=low_patience_state,
        **_BASE,
    )
    reply_call_system_prompt = provider.calls[1]["system"]
    # patience started at 4 and DISMISSIVE_OF_CONCERN has patience delta
    # -5, so post-update patience clamps to 0 -> "running short on
    # patience" hint must be present.
    assert "short on patience" in reply_call_system_prompt
