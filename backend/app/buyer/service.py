"""
Public entrypoint for the buyer module — this is what a future Phase 7
conversation API route calls, and what Phase 6 tests call directly.

Deliberately does not touch the database or FastAPI: per ARCHITECTURE.md,
`buyer/` owns the hidden-state schema + the LangGraph turn graph, while
persistence and turn-taking/end-condition logic belong to `conversation/`
(Phase 7). Keeping that boundary now, rather than reaching ahead into
Phase 7's job, is what the Phase 6 prompt's "PHASE BOUNDARY" section asks
for.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.ai.provider import LLMProvider
from app.buyer.classification import RepBehavior
from app.buyer.graph import get_compiled_graph
from app.buyer.state import BuyerState


@dataclass
class BuyerTurnResult:
    buyer_reply: str
    new_state: BuyerState
    classified_behavior: RepBehavior
    degraded: bool  # true if classification and/or reply generation fell back


def run_buyer_turn(
    provider: LLMProvider,
    *,
    rep_message: str,
    current_state: BuyerState,
    persona_name: str,
    persona_description: str,
    product_context: str,
    known_objection: str,
    turn_index: int = 0,
) -> BuyerTurnResult:
    """Runs exactly one buyer turn: classify -> deterministic state update
    -> generate reply. Never raises for LLM-related failures — those are
    absorbed into `degraded=True` with a safe fallback reply and an
    UNCLEAR classification (see classify.py / response.py)."""
    graph = get_compiled_graph()
    result = graph.invoke(
        {
            "rep_message": rep_message,
            "turn_index": turn_index,
            "persona_name": persona_name,
            "persona_description": persona_description,
            "product_context": product_context,
            "known_objection": known_objection,
            "current_state": current_state,
            "provider": provider,
        }
    )

    return BuyerTurnResult(
        buyer_reply=result["buyer_reply"],
        new_state=result["new_state"],
        classified_behavior=result["classification"].behavior,
        degraded=bool(result.get("classification_degraded")) or bool(result.get("reply_degraded")),
    )
