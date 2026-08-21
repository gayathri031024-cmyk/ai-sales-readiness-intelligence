"""Buyer state schema: bounds, clamping, purity of apply_deltas."""
from app.buyer.state import BuyerState, StateDelta, clamp


def test_state_within_bounds_is_unchanged():
    s = BuyerState(trust=45, patience=60, budget_sensitivity=80, interest=55)
    assert s.trust == 45
    assert s.patience == 60
    assert s.budget_sensitivity == 80
    assert s.interest == 55


def test_state_clamps_values_above_max_on_construction():
    s = BuyerState(trust=150, patience=200, budget_sensitivity=999, interest=101)
    assert s.trust == 100
    assert s.patience == 100
    assert s.budget_sensitivity == 100
    assert s.interest == 100


def test_state_clamps_values_below_min_on_construction():
    s = BuyerState(trust=-50, patience=-1, budget_sensitivity=-999, interest=0)
    assert s.trust == 0
    assert s.patience == 0
    assert s.budget_sensitivity == 0
    assert s.interest == 0


def test_clamp_helper_bounds_correctly():
    assert clamp(-5) == 0
    assert clamp(0) == 0
    assert clamp(50) == 50
    assert clamp(100) == 100
    assert clamp(101) == 100


def test_apply_deltas_is_pure_and_does_not_mutate_original():
    s = BuyerState(trust=50, patience=50, budget_sensitivity=50, interest=50)
    delta = StateDelta(trust=10, patience=-10, budget_sensitivity=0, interest=5)
    s2 = s.apply_deltas(delta)

    # original untouched
    assert s.trust == 50
    assert s.patience == 50
    assert s.budget_sensitivity == 50
    assert s.interest == 50

    # new instance reflects deltas
    assert s2.trust == 60
    assert s2.patience == 40
    assert s2.budget_sensitivity == 50
    assert s2.interest == 55
    assert s2 is not s


def test_apply_deltas_clamps_at_boundaries():
    s = BuyerState(trust=95, patience=5, budget_sensitivity=50, interest=50)
    delta = StateDelta(trust=20, patience=-20, budget_sensitivity=0, interest=0)
    s2 = s.apply_deltas(delta)
    assert s2.trust == 100  # clamped, not 115
    assert s2.patience == 0  # clamped, not -15


def test_only_four_documented_dimensions_exist():
    # Guards against scope creep — Phase 0 explicitly caps this at
    # "3-4 dimensions, not 7+".
    fields = set(BuyerState.model_fields.keys())
    assert fields == {"trust", "patience", "budget_sensitivity", "interest"}
