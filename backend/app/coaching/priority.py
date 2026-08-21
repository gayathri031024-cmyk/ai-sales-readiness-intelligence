"""
Deterministic coaching-priority selection.

Per this phase's rule 12 ("preserve the deterministic readiness decision
engine") and rule 15 ("prevent hallucinated coaching claims"), the
question of WHICH competency a rep should focus on first is answered by
comparing already-persisted numbers (score vs. threshold) — never left to
the LLM to decide. This mirrors `readiness/decision.py`'s own reasoning
exactly and reuses its `CompetencyResult` dataclass rather than defining
a second, slightly-different one.

The LLM's job (see `generation.py`) is narrower: given this module's
already-decided priority pick, write grounded, human-readable coaching
text about it. It never chooses the priority itself.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.readiness.decision import CompetencyResult


@dataclass(frozen=True)
class PriorityPick:
    competency_key: str
    display_name: str
    reason: str


class NoCompetencyResultsError(Exception):
    """Same invariant-violation semantics as readiness/decision.py's
    identically-named error — every conversation is always evaluated
    against all 3 MVP competencies (Phase 8), so an empty list here means
    something upstream is broken, not a legitimate empty case."""


def _tie_break_key(result: CompetencyResult, order: tuple[str, ...]) -> int:
    try:
        return order.index(result.competency_key)
    except ValueError:
        return len(order)  # unknown key sorts last — never crashes on it


def pick_priority(results: list[CompetencyResult], competency_order: tuple[str, ...]) -> PriorityPick:
    """If any competency failed its threshold: pick the failing one with
    the LARGEST gap (the worst offender — most impactful to fix first).
    If every competency passed (the conversation is READY): pick the
    PASSING one with the SMALLEST margin (the closest call — most likely
    to slip next time without continued attention). Ties are broken by
    `competency_order` (the fixed MVP competency ordering) so the pick is
    fully deterministic, never arbitrary dict/list ordering.
    """
    if not results:
        raise NoCompetencyResultsError("pick_priority requires at least one competency result")

    failing = [r for r in results if not r.passed]

    if failing:
        worst = sorted(failing, key=lambda r: (-r.gap, _tie_break_key(r, competency_order)))[0]
        reason = (
            f"{worst.display_name} has the largest gap to its threshold "
            f"({worst.gap} points) among your evaluated competencies."
        )
        return PriorityPick(competency_key=worst.competency_key, display_name=worst.display_name, reason=reason)

    closest = sorted(results, key=lambda r: (r.score - r.min_score, _tie_break_key(r, competency_order)))[0]
    margin = closest.score - closest.min_score
    reason = (
        f"{closest.display_name} passed with the narrowest margin ({margin} points above "
        f"threshold) among your evaluated competencies — worth continued attention."
    )
    return PriorityPick(competency_key=closest.competency_key, display_name=closest.display_name, reason=reason)
