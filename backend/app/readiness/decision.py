"""
Deterministic readiness decision (ARCHITECTURE.md §3: "`readiness/`
never calls an LLM. It only ever reads competency scores + scenario-
specific thresholds and returns READY / NOT READY / AT RISK with a
reason string built from which threshold(s) failed."; MASTER_PROMPT.md
READINESS ENGINE: "The LLM never decides readiness directly ... A
deterministic rules engine converts competency scores into READY /
NOT READY / AT RISK, using scenario-specific thresholds.")

Intentionally pure Python: no LLM call, no DB session, no import from
`app.ai` at all — this is the module boundary DECISIONS.md's Phase 1
entry ("Readiness engine is deterministic Python, never an LLM call")
exists to make enforceable in code, not just described in a prompt.
Easily unit-tested in complete isolation from the rest of the system.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Verdict = Literal["READY", "NOT_READY", "AT_RISK"]

# How many points below a competency's required minimum still counts as
# "borderline" (AT_RISK) rather than a clear miss (NOT_READY).
#
# Nothing in MASTER_PROMPT.md, ARCHITECTURE.md, or DATA_MODEL.md specifies
# this margin numerically — all three name READY/NOT_READY/AT_RISK as the
# three verdicts, but nothing distinguishes the latter two with a number.
# Rather than guess silently, this constant makes the judgment call
# explicit and documented, in the same spirit as `scenario/service.py`'s
# `_MVP_COMPETENCIES` threshold values themselves (that module's own
# comment: "a product judgment call ... revisit if Phase 15 stress
# testing shows these don't produce a sane spread"). See DECISIONS.md,
# Phase 9, for the full reasoning and the alternatives considered.
AT_RISK_MARGIN = 10


@dataclass(frozen=True)
class CompetencyResult:
    """Already-resolved input to the decision — a real evaluation score
    paired with this scenario's real threshold for that competency. This
    function only ever compares numbers already handed to it; it never
    looks anything up itself."""

    competency_key: str
    display_name: str
    score: int
    min_score: int

    @property
    def passed(self) -> bool:
        return self.score >= self.min_score

    @property
    def gap(self) -> int:
        """Positive = short of the threshold by this many points.
        Zero or negative = met or exceeded it."""
        return self.min_score - self.score


@dataclass(frozen=True)
class ReadinessDecision:
    verdict: Verdict
    reasoning: str


class NoCompetencyResultsError(Exception):
    """Raised if `decide_readiness` is called with an empty list — a
    service-layer invariant violation (every conversation is always
    evaluated against all 3 MVP competencies, per Phase 8), not a
    legitimate empty case this function should paper over."""


def _format_shortfall(result: CompetencyResult) -> str:
    return (
        f"{result.display_name} scored {result.score}, below the required "
        f"minimum of {result.min_score} for this scenario."
    )


def decide_readiness(results: list[CompetencyResult]) -> ReadinessDecision:
    """READY: every competency met its threshold.
    AT_RISK: at least one competency missed its threshold, but none missed
    it by more than `AT_RISK_MARGIN` points — a borderline performance.
    NOT_READY: at least one competency missed its threshold by more than
    `AT_RISK_MARGIN` points — a clear gap, not just a near miss.
    """
    if not results:
        raise NoCompetencyResultsError("decide_readiness requires at least one competency result")

    failing = [r for r in results if not r.passed]

    if not failing:
        return ReadinessDecision(
            verdict="READY",
            reasoning="All competencies met their required thresholds for this scenario.",
        )

    worst_gap = max(r.gap for r in failing)
    reasoning = " ".join(_format_shortfall(r) for r in failing)

    if worst_gap <= AT_RISK_MARGIN:
        return ReadinessDecision(verdict="AT_RISK", reasoning=reasoning)

    return ReadinessDecision(verdict="NOT_READY", reasoning=reasoning)
