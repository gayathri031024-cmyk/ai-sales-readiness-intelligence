"""
LLM provider abstraction.

Why this exists (see DECISIONS.md / MASTER_PROMPT.md AI RELIABILITY):
Every AI-touching module (buyer, later evaluation) talks to an
`LLMProvider`, never to a concrete SDK client directly. This lets:

- production use a real Anthropic client, configured purely from
  environment variables (LLM_API_KEY / LLM_MODEL — see core/config.py),
- automated tests run a fully deterministic `MockLLMProvider` with zero
  network calls and zero API cost,
- the real key be added later (Phase 6 -> final integration) with no
  code change, only an env var.

`LLMProvider.complete()` takes a system prompt + user prompt and returns
raw text. Structured-output parsing/validation/retry lives one layer up,
in `structured.py`, so this file stays a thin, swappable transport.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol


class LLMUnavailableError(Exception):
    """Raised when a provider cannot produce a completion at all
    (timeout, API error, missing key). Callers must catch this and
    degrade gracefully — never let it propagate as an unhandled 500."""


class LLMProvider(Protocol):
    def complete(self, *, system: str, user: str, max_tokens: int = 1000) -> str:
        """Return raw completion text, or raise LLMUnavailableError."""
        ...


class AnthropicProvider:
    """Production provider. Only imports/instantiates the SDK client when
    actually used — constructing this class does not require a key, but
    calling `complete()` without one raises LLMUnavailableError rather
    than a raw SDK exception, so degradation is uniform across providers.
    """

    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client = None  # lazily constructed on first real call

    def _get_client(self):
        if self._client is None:
            if not self._api_key or self._model == "not-configured":
                raise LLMUnavailableError(
                    "LLM_API_KEY / LLM_MODEL not configured — cannot reach a real provider."
                )
            import anthropic  # local import: never required for mock-only test runs

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(self, *, system: str, user: str, max_tokens: int = 1000) -> str:
        try:
            client = self._get_client()
            response = client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
            return "\n".join(parts)
        except LLMUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any SDK/network
            # failure degrades the same way, per ARCHITECTURE.md §7.
            raise LLMUnavailableError(f"Anthropic call failed: {exc}") from exc


class GeminiProvider:
    """Production provider using Google's Gemini API. Same contract as
    AnthropicProvider — a free-tier drop-in for when there's no budget
    for paid credits. Get a key (no card required) at
    https://aistudio.google.com/apikey and set LLM_PROVIDER=gemini,
    LLM_API_KEY=<that key>, LLM_MODEL=gemini-2.5-flash (or similar).
    """

    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client = None  # lazily constructed on first real call

    def _get_client(self):
        if self._client is None:
            if not self._api_key or self._model == "not-configured":
                raise LLMUnavailableError(
                    "LLM_API_KEY / LLM_MODEL not configured — cannot reach a real provider."
                )
            import google.generativeai as genai  # local import: never required for mock-only test runs

            genai.configure(api_key=self._api_key)
            self._client = genai

        return self._client

    def complete(self, *, system: str, user: str, max_tokens: int = 1000) -> str:
        try:
            genai = self._get_client()
            model = genai.GenerativeModel(model_name=self._model, system_instruction=system)
            response = model.generate_content(
                user,
                generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens),
            )
            return (response.text or "").strip()
        except LLMUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any SDK/network
            # failure degrades the same way, per ARCHITECTURE.md §7.
            raise LLMUnavailableError(f"Gemini call failed: {exc}") from exc


@dataclass
class MockLLMProvider:
    """Deterministic test double. No network, no cost, no API key.

    `responses` is an ordered queue of canned replies consumed one per
    call — lets a test script a specific sequence (e.g. malformed JSON
    once, then valid JSON, to exercise retry-once behavior). When the
    queue is empty, `default_response` (or `default_fn`, if set) is used
    forever. `fail_after` / `always_fail` simulate provider outages to
    exercise graceful-degradation paths without any real network flake.
    """

    responses: list[str] = field(default_factory=list)
    default_response: str = "{}"
    default_fn: Callable[[str, str], str] | None = None
    always_fail: bool = False
    calls: list[dict] = field(default_factory=list)

    def complete(self, *, system: str, user: str, max_tokens: int = 1000) -> str:
        self.calls.append({"system": system, "user": user, "max_tokens": max_tokens})
        if self.always_fail:
            raise LLMUnavailableError("MockLLMProvider configured to always fail.")
        if self.responses:
            return self.responses.pop(0)
        if self.default_fn is not None:
            return self.default_fn(system, user)
        return self.default_response