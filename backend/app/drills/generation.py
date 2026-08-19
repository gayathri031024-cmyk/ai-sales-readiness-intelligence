"""
Targeted drill generation (Phase 11).

MASTER_PROMPT.md's TRAINING LOOP: "Weakness → targeted drill → practice
→ reassessment → competency achieved." This module builds the "targeted
drill" step from Phase 10's already-generated, already-verified coaching
output — Phase 9's deterministic priority pick, and the coaching points
`coaching/verification.py` already proved are grounded in real Phase 8
evidence.

Deliberately makes ZERO LLM calls, the same posture as `readiness/`
(ARCHITECTURE.md §3) rather than `coaching/`'s one narrow LLM call. See
DECISIONS.md, Phase 11, for the full reasoning — in short: every fact a
drill could need (which competency, why, what to work on, supporting
evidence) was already generated and verified by Phase 8/9/10. Re-asking
an LLM to write about the same facts a third time would only add cost
and a fresh hallucination surface for zero new information. This module
is pure reassembly — a deterministic Python function, trivially
unit-testable, that can never introduce a claim Phase 8/10 didn't
already verify.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DrillPoint:
    """One already-grounded coaching point being carried into the drill,
    filtered to the priority competency. Mirrors
    `coaching/verification.py::VerifiedCoachingPoint`'s shape exactly —
    this module never re-verifies grounding, since these points already
    passed Phase 10's verification and are being carried forward
    unchanged, not re-derived."""

    competency_key: str
    evidence_id: str | None
    message: str


@dataclass(frozen=True)
class GeneratedDrill:
    title: str
    focus_reason: str
    instructions: str
    focus_points: list[DrillPoint]


def _select_focus_points(all_points: list[dict], priority_competency_key: str) -> list[DrillPoint]:
    return [
        DrillPoint(competency_key=p["competency_key"], evidence_id=p.get("evidence_id"), message=p["message"])
        for p in all_points
        if p["competency_key"] == priority_competency_key
    ]


def _build_instructions(
    priority_display_name: str,
    priority_reason: str,
    diagnosis: str,
    recommendation: str,
    focus_points: list[DrillPoint],
) -> str:
    """Assembles instruction text entirely from already-verified upstream
    text — the evaluation's own diagnosis/recommendation for this
    competency (Phase 8) and the coaching priority reason (Phase 9/10).
    No new claim is introduced; this is reordering and light connective
    text only."""
    lines = [
        f"Focus competency: {priority_display_name}.",
        priority_reason,
        "",
        f"What the last evaluation showed: {diagnosis}",
        f"Recommended focus: {recommendation}",
    ]
    if focus_points:
        lines.append("")
        lines.append("Coaching points to keep in mind while you practice:")
        for point in focus_points:
            lines.append(f"- {point.message}")
    return "\n".join(lines)


def generate_drill(
    priority_competency_key: str,
    priority_display_name: str,
    priority_reason: str,
    diagnosis: str,
    recommendation: str,
    coaching_points: list[dict],
) -> GeneratedDrill:
    """Pure function — no LLM, no DB, no I/O. `coaching_points` is the
    full list of a conversation's already-persisted, already-verified
    `CoachingSession.points` (Phase 10); this function filters it down
    to only the priority competency's points rather than re-verifying
    anything, since verification already happened once."""
    focus_points = _select_focus_points(coaching_points, priority_competency_key)
    instructions = _build_instructions(
        priority_display_name, priority_reason, diagnosis, recommendation, focus_points
    )
    return GeneratedDrill(
        title=f"Practice: {priority_display_name}",
        focus_reason=priority_reason,
        instructions=instructions,
        focus_points=focus_points,
    )
