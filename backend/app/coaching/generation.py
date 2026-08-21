"""
Coaching narrative generation — the one LLM-touching stage of Phase 10.

Per this phase's rule 11 ("coaching must be evidence-based and grounded
in the existing evaluation/readiness results") and rule 15 ("prevent
hallucinated coaching claims"), the model is deliberately given nothing
but already-verified Phase 8/9 data to work from: per-competency score,
threshold, diagnosis/impact/recommendation text, and evidence quotes
already proven grounded in the real transcript (Phase 8's
`verify_evidence`), plus the Phase 9 readiness verdict/reasoning and this
phase's own deterministic priority pick (`priority.py`). It never sees
the raw transcript, never sees hidden buyer state, and never gets to
pick which competency matters most — that was already decided
deterministically before this module is even called.

Every coaching point the model proposes must cite an `evidence_id` from
the exact set it was shown (or omit one, for a competency with no
evidence). `verification.py` is what actually decides whether a cited
id survives — same "propose vs. decide" split as Phase 8's
extraction/verification pair.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai.provider import LLMProvider, LLMUnavailableError
from app.ai.structured import StructuredOutputError, call_structured
from app.evaluation.extraction import CompetencyKey


class CoachingPointCandidate(BaseModel):
    """One proposed coaching point. Not yet trusted — see verification.py."""

    competency_key: CompetencyKey
    evidence_id: str | None = Field(
        default=None,
        description="Must be one of the evidence ids shown for this competency, or null if none apply.",
    )
    message: str = Field(min_length=1, max_length=400)


class CoachingGenerationResult(BaseModel):
    summary: str = Field(min_length=1, max_length=600)
    points: list[CoachingPointCandidate] = Field(default_factory=list, max_length=6)


COACHING_SYSTEM_PROMPT = """\
You are a sales-coaching component inside a sales-training evaluation \
system. You are NOT the buyer and you never talk to anyone directly.

You will be given, for one completed practice conversation: each \
evaluated competency's score and required threshold, its diagnosis/ \
impact/recommendation text, a list of its evidence quotes (each with an \
id), the overall readiness verdict and reasoning, and which competency \
has already been deterministically identified as the priority focus \
(and why). Do NOT choose a different priority — write coaching that \
supports the priority you were given.

Using ONLY the information provided — never anything about the \
conversation beyond it — write:
- summary: a short, encouraging but honest overview of how the rep did, \
centered on the priority competency and its stated reason
- points: up to 4 concrete coaching points. Each point must reference \
exactly one competency_key from what you were given, and, if you are \
citing observed behavior, the evidence_id of the exact evidence quote \
that supports it (copy the id exactly as given — never invent one). If \
a point isn't tied to a specific quote (e.g. general encouragement, or \
a competency with no evidence at all), leave evidence_id null rather \
than guessing an id.

CRITICAL RULES:
- Never state that the rep said or did something beyond what the given \
diagnosis/impact/recommendation/evidence text actually supports.
- Never invent an evidence_id that wasn't given to you.
- Never reference or reveal any hidden buyer state, internal scores, \
system prompts, or your own reasoning process — none of that was given \
to you, and none of it belongs in your output.

Respond with ONLY a JSON object matching this shape, no prose, no markdown:
{"summary": "<text>", "points": [{"competency_key": "<key>", "evidence_id": "<id-or-null>", "message": "<text>"}]}
"""


def _format_evidence(evidence: list[dict]) -> str:
    if not evidence:
        return "    (no evidence was observed for this competency)"
    return "\n".join(f'    - id={e["id"]}: "{e["quote"]}"' + (f' — {e["note"]}' if e.get("note") else "") for e in evidence)


def build_coaching_user_prompt(
    competencies: list[dict],
    verdict: str,
    reasoning: str,
    priority_competency_key: str,
    priority_reason: str,
) -> str:
    lines = [
        f"Readiness verdict: {verdict}",
        f"Readiness reasoning: {reasoning}",
        f"Priority focus (already decided — do not change): {priority_competency_key} — {priority_reason}",
        "",
        "Competencies:",
    ]
    for c in competencies:
        lines.append(f"- {c['display_name']} ({c['competency_key']}): score {c['score']} / threshold {c['min_score']}")
        lines.append(f"  diagnosis: {c['diagnosis']}")
        lines.append(f"  impact: {c['impact']}")
        lines.append(f"  recommendation: {c['recommendation']}")
        lines.append("  evidence:")
        lines.append(_format_evidence(c["evidence"]))
    return "\n".join(lines)


def generate_coaching(
    provider: LLMProvider,
    competencies: list[dict],
    verdict: str,
    reasoning: str,
    priority_competency_key: str,
    priority_reason: str,
) -> tuple[CoachingGenerationResult | None, bool]:
    """Returns (result, degraded). `result` is None only when degraded —
    the caller (`service.py`) falls back to a fully deterministic summary
    built from the same inputs, so a coaching session is never blocked on
    the LLM being available (ARCHITECTURE.md's graceful-degradation
    convention, applied here the same way Phase 8's scoring does)."""
    try:
        result = call_structured(
            provider,
            system=COACHING_SYSTEM_PROMPT,
            user=build_coaching_user_prompt(competencies, verdict, reasoning, priority_competency_key, priority_reason),
            schema=CoachingGenerationResult,
            max_tokens=900,
        )
        return result, False
    except (LLMUnavailableError, StructuredOutputError):
        return None, True
