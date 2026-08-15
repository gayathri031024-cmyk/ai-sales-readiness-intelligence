"""
Generates the buyer's in-character reply, and provides the graceful
fallback used when the LLM is unavailable (ARCHITECTURE.md §7: "second
failure -> graceful degraded response, not a crash").

Also implements a defense-in-depth scrubber: the prompt in persona.py is
the primary defense against state leakage (the model never even sees
the numbers), but per MASTER_PROMPT.md's AI RELIABILITY section
("hallucination" is an explicit risk to account for), a second,
independent layer catches the case where a reply nonetheless contains
something that looks like a leaked internal value or an
acknowledgement of these hidden mechanics, and replaces it with a safe
generic line rather than shipping the raw output.
"""
from __future__ import annotations

import re

from app.ai.provider import LLMProvider, LLMUnavailableError
from app.buyer.persona import build_buyer_system_prompt, build_buyer_user_prompt
from app.buyer.state import BuyerState

# Deliberately generic phrases only — a real buyer redirecting an odd
# remark, not a system message. Kept short since this is a last-resort
# fallback path, expected to be rare.
FALLBACK_REPLIES = [
    "Sorry, can we get back to what we were discussing?",
    "I'm not sure what you mean — let's stay focused on the deal at hand.",
    "Let's keep this on track. Where were we?",
]

# Defense-in-depth only — not the primary control (see persona.py rule
# #2/#3). Flags replies that talk *about* the hidden mechanics rather
# than being a normal buyer line. Deliberately narrow, so it doesn't
# false-positive on ordinary conversation (e.g. the buyer legitimately
# discussing "trust" in a business sense, or "my patience with vendors").
_LEAK_PATTERNS = [
    re.compile(r"\btrust\s*(level|score|is|:)\s*\d", re.IGNORECASE),
    re.compile(r"\bpatience\s*(level|score|is|:)\s*\d", re.IGNORECASE),
    re.compile(r"\b(budget[ _-]?sensitivity|interest)\s*(level|score|is|:)\s*\d", re.IGNORECASE),
    re.compile(r"\bas an ai\b", re.IGNORECASE),
    re.compile(r"\bsystem prompt\b", re.IGNORECASE),
    re.compile(r"\b(my|the) instructions (say|are|were)\b", re.IGNORECASE),
    re.compile(r"\bhidden state\b", re.IGNORECASE),
    re.compile(r"\binternal reasoning\b", re.IGNORECASE),
]


def _looks_like_leak(text: str) -> bool:
    return any(p.search(text) for p in _LEAK_PATTERNS)


def fallback_reply(turn_index: int) -> str:
    return FALLBACK_REPLIES[turn_index % len(FALLBACK_REPLIES)]


def generate_buyer_reply(
    provider: LLMProvider,
    *,
    persona_name: str,
    persona_description: str,
    product_context: str,
    known_objection: str,
    state: BuyerState,
    rep_message: str,
    turn_index: int,
) -> tuple[str, bool]:
    """Returns (reply_text, degraded). `degraded=True` means the LLM was
    unavailable or its output tripped the leak scrubber, and a safe
    fallback line was substituted."""
    system = build_buyer_system_prompt(
        persona_name=persona_name,
        persona_description=persona_description,
        product_context=product_context,
        known_objection=known_objection,
        state=state,
    )
    user = build_buyer_user_prompt(rep_message)

    try:
        raw = provider.complete(system=system, user=user, max_tokens=400).strip()
    except LLMUnavailableError:
        return fallback_reply(turn_index), True

    if not raw or _looks_like_leak(raw):
        return fallback_reply(turn_index), True

    return raw, False
