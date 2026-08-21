"""
Calls the LLM to classify a rep message, using the shared structured-
output helper (app/ai/structured.py) for schema validation + retry-once.

Kept separate from classification.py (which only defines the schema and
prompts, no I/O) so the schema stays importable/testable without pulling
in the provider machinery.
"""
from __future__ import annotations

from app.ai.provider import LLMProvider, LLMUnavailableError
from app.ai.structured import StructuredOutputError, call_structured
from app.buyer.classification import (
    CLASSIFICATION_SYSTEM_PROMPT,
    RepBehavior,
    RepClassification,
    build_classification_user_prompt,
)


def classify_rep_message(provider: LLMProvider, rep_message: str) -> tuple[RepClassification, bool]:
    """Returns (classification, degraded). On any LLM failure (unavailable
    or unparseable after retry), degrades to RepBehavior.UNCLEAR rather
    than raising — classification failure must never crash a turn, per
    ARCHITECTURE.md §7."""
    try:
        result = call_structured(
            provider,
            system=CLASSIFICATION_SYSTEM_PROMPT,
            user=build_classification_user_prompt(rep_message),
            schema=RepClassification,
        )
        return result, False
    except (LLMUnavailableError, StructuredOutputError):
        return (
            RepClassification(
                behavior=RepBehavior.UNCLEAR,
                confidence=0.0,
                rationale="Classification unavailable; degraded to UNCLEAR.",
            ),
            True,
        )
