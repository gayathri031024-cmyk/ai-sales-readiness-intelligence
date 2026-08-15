"""
Structured-output helper shared by every AI call in the project
(buyer classification now; evaluation extraction in Phase 8 reuses this
same helper rather than growing a second copy — see ARCHITECTURE.md §4).

Contract (per ARCHITECTURE.md §7):
  - every LLM call that needs structured data asks for JSON matching a
    Pydantic schema,
  - the raw text is parsed and validated against that schema,
  - on failure (bad JSON, schema violation), retry exactly once with the
    validation error appended to the prompt so the model can self-correct,
  - a second failure raises StructuredOutputError — callers must catch
    this and degrade gracefully, never crash the request.
"""
from __future__ import annotations

import json
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.provider import LLMProvider, LLMUnavailableError

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(Exception):
    """Raised when the model's output cannot be coerced into the
    requested schema even after one retry."""


def _extract_json(text: str) -> str:
    """Models sometimes wrap JSON in prose or code fences despite
    instructions. Take the outermost {...} span rather than assuming
    the whole string is clean JSON."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return text
    return text[start : end + 1]


def call_structured(
    provider: LLMProvider,
    *,
    system: str,
    user: str,
    schema: Type[T],
    max_tokens: int = 500,
) -> T:
    """Call `provider` and parse/validate the result as `schema`.
    Retries once on malformed JSON or schema validation failure.
    Raises StructuredOutputError on a second failure, or if the
    provider itself is unavailable (caller decides how to degrade)."""

    last_error: str | None = None
    for attempt in range(2):
        prompt = user
        if last_error is not None:
            prompt = (
                f"{user}\n\n"
                f"Your previous response was invalid: {last_error}\n"
                f"Respond again with ONLY valid JSON matching the required schema. "
                f"No prose, no markdown code fences."
            )
        try:
            raw = provider.complete(system=system, user=prompt, max_tokens=max_tokens)
        except LLMUnavailableError:
            # Not a structured-output problem — a transport problem.
            # Let it propagate so the caller's degradation path (which
            # already has to handle LLMUnavailableError) handles it,
            # rather than masking it as a StructuredOutputError.
            raise

        try:
            candidate = json.loads(_extract_json(raw))
            return schema.model_validate(candidate)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)
            continue

    raise StructuredOutputError(
        f"Model output did not match {schema.__name__} after retry. Last error: {last_error}"
    )
