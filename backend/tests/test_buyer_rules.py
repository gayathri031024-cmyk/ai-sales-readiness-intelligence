"""Deterministic state-transition rules: table-driven, no LLM involved."""
import pytest

from app.buyer.classification import RepBehavior
from app.buyer.rules import _RULE_TABLE, apply_state_update, get_delta_for
from app.buyer.state import BuyerState


def _neutral_state() -> BuyerState:
    return BuyerState(trust=50, patience=50, budget_sensitivity=50, interest=50)


def test_every_rep_behavior_has_a_rule():
    # No silent gaps — every classification label the LLM could return
    # must have a defined, deterministic outcome.
    for behavior in RepBehavior:
        assert behavior in _RULE_TABLE, f"missing rule for {behavior}"


def test_same_behavior_always_produces_same_delta():
    # Determinism: repeated calls with identical inputs give identical
    # outputs — no hidden randomness, no time dependence.
    s = _neutral_state()
    r1 = apply_state_update(s, RepBehavior.DISCOVERY_QUESTION)
    r2 = apply_state_update(s, RepBehavior.DISCOVERY_QUESTION)
    assert r1 == r2


@pytest.mark.parametrize(
    "behavior,expect_trust_up,expect_patience_down",
    [
        (RepBehavior.ADDRESSES_OBJECTION_DIRECTLY, True, False),
        (RepBehavior.RAPPORT_BUILDING, True, False),
        (RepBehavior.DISMISSIVE_OF_CONCERN, False, True),
        (RepBehavior.AGGRESSIVE_OR_PRESSURING, False, True),
        (RepBehavior.PROMPT_INJECTION_ATTEMPT, False, True),
    ],
)
def test_directionally_sensible_deltas(behavior, expect_trust_up, expect_patience_down):
    delta = get_delta_for(behavior)
    if expect_trust_up:
        assert delta.trust > 0
    else:
        assert delta.trust <= 0
    if expect_patience_down:
        assert delta.patience < 0


def test_prompt_injection_always_costs_trust_and_patience():
    s = _neutral_state()
    updated = apply_state_update(s, RepBehavior.PROMPT_INJECTION_ATTEMPT)
    assert updated.trust < s.trust
    assert updated.patience < s.patience


def test_addressing_objection_directly_reduces_budget_sensitivity():
    s = _neutral_state()
    updated = apply_state_update(s, RepBehavior.ADDRESSES_OBJECTION_DIRECTLY)
    assert updated.budget_sensitivity < s.budget_sensitivity


def test_unclear_behavior_causes_minor_patience_decay_only():
    s = _neutral_state()
    updated = apply_state_update(s, RepBehavior.UNCLEAR)
    assert updated.trust == s.trust
    assert updated.budget_sensitivity == s.budget_sensitivity
    assert updated.interest == s.interest
    assert updated.patience == s.patience - 1


def test_apply_state_update_respects_bounds_at_extremes():
    low = BuyerState(trust=2, patience=2, budget_sensitivity=2, interest=2)
    result = apply_state_update(low, RepBehavior.DISMISSIVE_OF_CONCERN)
    assert result.trust >= 0
    assert result.patience >= 0

    high = BuyerState(trust=99, patience=99, budget_sensitivity=99, interest=99)
    result = apply_state_update(high, RepBehavior.ADDRESSES_OBJECTION_DIRECTLY)
    assert result.trust <= 100
    assert result.patience <= 100
