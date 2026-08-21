"""LLM provider abstraction: mock determinism, structured-output
validation, retry-once behavior, and graceful failure — all without any
real network call or API key. See app/ai/provider.py, app/ai/structured.py.
"""
import json

import pytest
from pydantic import BaseModel

from app.ai.provider import AnthropicProvider, LLMUnavailableError, MockLLMProvider
from app.ai.structured import StructuredOutputError, call_structured


class _Widget(BaseModel):
    name: str
    count: int


def test_mock_provider_returns_queued_responses_in_order():
    provider = MockLLMProvider(responses=["first", "second"])
    assert provider.complete(system="s", user="u") == "first"
    assert provider.complete(system="s", user="u") == "second"


def test_mock_provider_falls_back_to_default_after_queue_empties():
    provider = MockLLMProvider(responses=["only"], default_response="fallback")
    provider.complete(system="s", user="u")
    assert provider.complete(system="s", user="u") == "fallback"
    assert provider.complete(system="s", user="u") == "fallback"


def test_mock_provider_records_calls():
    provider = MockLLMProvider(default_response="x")
    provider.complete(system="sys-prompt", user="user-prompt", max_tokens=123)
    assert len(provider.calls) == 1
    assert provider.calls[0]["system"] == "sys-prompt"
    assert provider.calls[0]["user"] == "user-prompt"
    assert provider.calls[0]["max_tokens"] == 123


def test_mock_provider_always_fail_raises_unavailable():
    provider = MockLLMProvider(always_fail=True)
    with pytest.raises(LLMUnavailableError):
        provider.complete(system="s", user="u")


def test_anthropic_provider_raises_unavailable_without_key():
    provider = AnthropicProvider(api_key=None, model="not-configured")
    with pytest.raises(LLMUnavailableError):
        provider.complete(system="s", user="u")
    # Constructing the provider itself must never require a key or make
    # a network call — only calling complete() should fail.


def test_call_structured_parses_valid_json_first_try():
    provider = MockLLMProvider(responses=[json.dumps({"name": "widget", "count": 3})])
    result = call_structured(provider, system="s", user="u", schema=_Widget)
    assert result == _Widget(name="widget", count=3)
    assert len(provider.calls) == 1


def test_call_structured_retries_once_on_malformed_json_then_succeeds():
    provider = MockLLMProvider(
        responses=["not json at all", json.dumps({"name": "widget", "count": 3})]
    )
    result = call_structured(provider, system="s", user="u", schema=_Widget)
    assert result == _Widget(name="widget", count=3)
    assert len(provider.calls) == 2
    # The retry prompt should include the validation failure so the
    # model can self-correct.
    assert "invalid" in provider.calls[1]["user"].lower()


def test_call_structured_retries_once_on_schema_violation_then_succeeds():
    provider = MockLLMProvider(
        responses=[json.dumps({"name": "widget"}), json.dumps({"name": "widget", "count": 5})]
    )
    result = call_structured(provider, system="s", user="u", schema=_Widget)
    assert result.count == 5
    assert len(provider.calls) == 2


def test_call_structured_raises_after_second_failure():
    provider = MockLLMProvider(responses=["garbage", "still garbage"])
    with pytest.raises(StructuredOutputError):
        call_structured(provider, system="s", user="u", schema=_Widget)
    assert len(provider.calls) == 2  # exactly one retry, not infinite


def test_call_structured_extracts_json_wrapped_in_prose_or_fences():
    provider = MockLLMProvider(
        responses=['Sure, here you go:\n```json\n{"name": "widget", "count": 7}\n```\nHope that helps!']
    )
    result = call_structured(provider, system="s", user="u", schema=_Widget)
    assert result == _Widget(name="widget", count=7)


def test_call_structured_propagates_llm_unavailable_without_retry_loop():
    provider = MockLLMProvider(always_fail=True)
    with pytest.raises(LLMUnavailableError):
        call_structured(provider, system="s", user="u", schema=_Widget)
    # A transport failure should not be retried by call_structured itself
    # (that's a provider-level concern) — exactly one attempt.
    assert len(provider.calls) == 1
