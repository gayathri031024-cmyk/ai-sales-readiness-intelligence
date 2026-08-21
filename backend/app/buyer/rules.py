"""
Deterministic buyer state-transition rules.

This is the module ARCHITECTURE.md §4A and DECISIONS.md point to as the
enforceable half of "LLM classifies, Python decides": given a
`RepBehavior` label, this file is the *only* place that decides how
trust/patience/budget_sensitivity/interest change. It has no LLM
dependency, is pure (BuyerState in, BuyerState out, no I/O), and is
fully unit-testable as a plain lookup table.

Deliberately flat, not conditional-on-current-state: each label maps to
one fixed delta. Conditioning deltas on current state (e.g. "pushing to
close lands differently if trust is already low") is exactly the kind
of emergent complexity Phase 0/1 chose to defer — see DECISIONS.md
"Buyer state updates are deterministic ... not raw LLM-generated
numbers", tradeoff: "Less 'emergent' buyer behavior, more predictable
and testable — appropriate for an MVP." Revisit only with a documented
product reason, not by accretion.
"""
from __future__ import annotations

from app.buyer.classification import RepBehavior
from app.buyer.state import BuyerState, StateDelta

# trust, patience, budget_sensitivity, interest
_RULE_TABLE: dict[RepBehavior, StateDelta] = {
    RepBehavior.DISCOVERY_QUESTION: StateDelta(trust=3, patience=0, budget_sensitivity=0, interest=2),
    RepBehavior.VALUE_ARTICULATION: StateDelta(trust=1, patience=0, budget_sensitivity=-2, interest=4),
    RepBehavior.ADDRESSES_OBJECTION_DIRECTLY: StateDelta(
        trust=5, patience=2, budget_sensitivity=-5, interest=3
    ),
    RepBehavior.VAGUE_OR_EVASIVE: StateDelta(trust=-4, patience=-3, budget_sensitivity=0, interest=-1),
    RepBehavior.PUSHES_FOR_CLOSE: StateDelta(trust=0, patience=-2, budget_sensitivity=0, interest=0),
    RepBehavior.DISMISSIVE_OF_CONCERN: StateDelta(
        trust=-6, patience=-5, budget_sensitivity=2, interest=-3
    ),
    RepBehavior.RAPPORT_BUILDING: StateDelta(trust=2, patience=1, budget_sensitivity=0, interest=1),
    RepBehavior.AGGRESSIVE_OR_PRESSURING: StateDelta(
        trust=-5, patience=-6, budget_sensitivity=1, interest=-2
    ),
    # A manipulation attempt costs trust and patience regardless of
    # whether it "worked" — the buyer noticed, per the persona's
    # sophistication (see persona.py). Interest/budget_sensitivity are
    # untouched: this isn't a sales-technique signal at all.
    RepBehavior.PROMPT_INJECTION_ATTEMPT: StateDelta(trust=-8, patience=-5, budget_sensitivity=0, interest=0),
    # Small decay for a turn that didn't move the conversation anywhere —
    # not a punishment, just "nothing earned, time is passing."
    RepBehavior.UNCLEAR: StateDelta(trust=0, patience=-1, budget_sensitivity=0, interest=0),
}


def apply_state_update(state: BuyerState, behavior: RepBehavior) -> BuyerState:
    """The single entry point for turning a classified rep behavior into
    an updated buyer state. Bounded (via BuyerState's own clamping),
    pure, and deterministic — same (state, behavior) in, same state out,
    every time."""
    delta = _RULE_TABLE[behavior]
    return state.apply_deltas(delta)


def get_delta_for(behavior: RepBehavior) -> StateDelta:
    """Exposed for tests that want to assert on the table directly
    without going through a full BuyerState round-trip."""
    return _RULE_TABLE[behavior]
