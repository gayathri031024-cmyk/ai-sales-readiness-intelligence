"""
Builds the LLMProvider production code should use, from `Settings`
(env vars LLM_API_KEY / LLM_MODEL — see core/config.py).

Tests never call this — they construct a `MockLLMProvider` directly and
pass it explicitly into buyer/service functions. This file exists so
that *runtime* code (a future Phase 7 API route, for instance) has one
obvious place to get a real provider without knowing whether a key is
actually configured yet.
"""
from __future__ import annotations

from app.ai.provider import AnthropicProvider, GeminiProvider, LLMProvider
from app.core.config import Settings, get_settings


def build_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "gemini":
        return GeminiProvider(api_key=settings.llm_api_key, model=settings.llm_model)
    return AnthropicProvider(api_key=settings.llm_api_key, model=settings.llm_model)