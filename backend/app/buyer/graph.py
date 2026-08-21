"""
LangGraph implementation of the buyer turn pipeline described in
ARCHITECTURE.md §4A:

    receive_rep_message
            v
    classify_rep_behavior (structured output)
            v
    update_buyer_state (deterministic)
            v
    generate_buyer_reply (LLM, constrained)

`check_end_conditions` (turn limit / patience threshold / explicit
close) is explicitly conversation-engine territory — Phase 7, not
Phase 6 (see MASTER_PROMPT.md phase table, and this Phase 6 prompt's
"PHASE BOUNDARY" section) — so it is not part of this graph. This graph
covers exactly one turn: rep message in, updated state + buyer reply
out. A future Phase 7 graph/loop calls this repeatedly and owns the
looping/termination decision.

Kept intentionally small per the Phase 6 prompt ("Keep the graph small
and understandable"): three nodes, one straight line, no branching.
Graceful degradation is handled *inside* each node (classify.py and
response.py already degrade internally rather than raising), so the
graph itself never needs a failure branch — every node always produces
a valid output for the next node, degraded or not.
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.ai.provider import LLMProvider
from app.buyer.classification import RepClassification
from app.buyer.classify import classify_rep_message
from app.buyer.response import generate_buyer_reply
from app.buyer.rules import apply_state_update
from app.buyer.state import BuyerState


class BuyerTurnState(TypedDict, total=False):
    # --- inputs ---
    rep_message: str
    turn_index: int
    persona_name: str
    persona_description: str
    product_context: str
    known_objection: str
    current_state: BuyerState
    provider: LLMProvider

    # --- populated as the graph runs ---
    classification: RepClassification
    classification_degraded: bool
    new_state: BuyerState
    buyer_reply: str
    reply_degraded: bool


def _classify_node(state: BuyerTurnState) -> BuyerTurnState:
    classification, degraded = classify_rep_message(state["provider"], state["rep_message"])
    return {"classification": classification, "classification_degraded": degraded}


def _update_state_node(state: BuyerTurnState) -> BuyerTurnState:
    new_state = apply_state_update(state["current_state"], state["classification"].behavior)
    return {"new_state": new_state}


def _generate_reply_node(state: BuyerTurnState) -> BuyerTurnState:
    reply, degraded = generate_buyer_reply(
        state["provider"],
        persona_name=state["persona_name"],
        persona_description=state["persona_description"],
        product_context=state["product_context"],
        known_objection=state["known_objection"],
        state=state["new_state"],
        rep_message=state["rep_message"],
        turn_index=state["turn_index"],
    )
    return {"buyer_reply": reply, "reply_degraded": degraded}


def build_buyer_turn_graph():
    graph = StateGraph(BuyerTurnState)
    graph.add_node("classify_rep_behavior", _classify_node)
    graph.add_node("update_buyer_state", _update_state_node)
    graph.add_node("generate_buyer_reply", _generate_reply_node)

    graph.set_entry_point("classify_rep_behavior")
    graph.add_edge("classify_rep_behavior", "update_buyer_state")
    graph.add_edge("update_buyer_state", "generate_buyer_reply")
    graph.add_edge("generate_buyer_reply", END)

    return graph.compile()


# Compiled once at import time — the graph structure itself has no
# per-request state (that all lives in BuyerTurnState passed into
# .invoke()), so recompiling per call would be pure overhead.
_COMPILED_GRAPH = None


def get_compiled_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_buyer_turn_graph()
    return _COMPILED_GRAPH
