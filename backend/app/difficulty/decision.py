"""
Deterministic adaptive-difficulty recommendation (Phase 12).

MASTER_PROMPT.md CORE FEATURES #7: "Adaptive difficulty based on
performance", and this phase's own explicit instruction: "The
implementation must remain deterministic and must NOT allow an LLM to
directly decide the difficulty." This module makes zero LLM calls,
structurally — no provider parameter exists in its function signature at
all, the same "living assertion" posture `drills/generation.py` and
`readiness/decision.py` already established (test-enforced).

Reuses `readiness/decision.py::CompetencyResult`/`Verdict` directly
rather than defining a second, slightly-different pair — the same reuse
discipline `coaching/priority.py` established one phase earlier. This
module only ever compares already-decided numbers (a readiness verdict,
per-competency score/threshold pairs, and a scenario's current
`difficulty` string) that were handed to it; it never looks anything up
or calls anything itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.readiness.decision import CompetencyResult, Verdict

Direction = Literal["increase", "maintain", "decrease"]

# The MVP's existing scenario difficulty ladder (DATA_MODEL.md:
# "difficulty | text | enum-like: easy/standard/hard"). Ordered
# low-to-high so a recommendation can step one rung up or down.
DIFFICULTY_LEVELS: tuple[str, ...] = ("easy", "standard", "hard")

# How many points of margin above threshold, on the *narrowest* passing
# competency, counts as "comfortably ready" (worth stepping up a
# difficulty level) rather than "just barely ready" (worth staying put
# to solidify first).
#
# Nothing in MASTER_PROMPT.md, ARCHITECTURE.md, or DATA_MODEL.md
# specifies this number — the same situation `readiness/decision.py`'s
# own `AT_RISK_MARGIN` was in. Rather than guess silently, this reuses
# that exact same value and the same reasoning: a judgment call made
# explicit and documented, not derived from real transcript data (none
# exists yet). Revisit alongside `AT_RISK_MARGIN` if Phase 15 stress
# testing shows either constant doesn't produce a sane spread. See
# DECISIONS.md, Phase 12.
READY_COMFORTABLE_MARGIN = 10


@dataclass(frozen=True)
class DifficultyRecommendation:
    recommended_difficulty: str
    current_difficulty: str
    direction: Direction
    verdict: Verdict
    reasoning: str


class NoCompetencyResultsError(Exception):
    """Same invariant-violation semantics as `readiness/decision.py`'s
    and `coaching/priority.py`'s identically-named errors — every
    conversation is always evaluated against all 3 MVP competencies
    (Phase 8), so an empty list here means something upstream is
    broken, not a legitimate empty case."""


class UnknownDifficultyError(Exception):
    """Raised if `current_difficulty` isn't one of `DIFFICULTY_LEVELS`.
    Should never happen against the seeded MVP scenario (always
    "standard"), but this module never silently treats an unrecognized
    value as a known one — same "guard, don't fabricate" posture as
    `readiness/service.py::ThresholdMissingError`."""


def _step(level: str, delta: int) -> str:
    """Move one rung up/down `DIFFICULTY_LEVELS`, clamped at either end
    — stepping down from "easy" or up from "hard" simply stays put."""
    index = DIFFICULTY_LEVELS.index(level)
    new_index = max(0, min(len(DIFFICULTY_LEVELS) - 1, index + delta))
    return DIFFICULTY_LEVELS[new_index]


def recommend_difficulty(
    results: list[CompetencyResult],
    verdict: Verdict,
    current_difficulty: str,
) -> DifficultyRecommendation:
    """Recommends the next scenario difficulty for this salesperson,
    given their already-decided Phase 9 readiness verdict and
    already-persisted Phase 8 competency scores/thresholds for the
    scenario they just attempted.

    Rules (mirrors `readiness/decision.py::decide_readiness`'s own
    three-way split, one layer up):

    - NOT_READY: a clear competency gap. Step DOWN one difficulty level
      (or stay at "easy" if already there — nowhere lower to go).
    - AT_RISK: a borderline miss. Stay at the current difficulty —
      neither a demonstrated gap nor a demonstrated comfortable pass.
    - READY, but narrowly (narrowest passing margin below
      `READY_COMFORTABLE_MARGIN`): stay at the current difficulty to
      solidify performance before increasing challenge.
    - READY, comfortably (narrowest passing margin at or above
      `READY_COMFORTABLE_MARGIN`): step UP one difficulty level (or
      stay at "hard" if already there — nowhere higher to go).
    """
    if current_difficulty not in DIFFICULTY_LEVELS:
        raise UnknownDifficultyError(
            f"Unknown scenario difficulty '{current_difficulty}' — expected one of {DIFFICULTY_LEVELS}"
        )
    if not results:
        raise NoCompetencyResultsError("recommend_difficulty requires at least one competency result")

    if verdict == "NOT_READY":
        target = _step(current_difficulty, -1)
        if target == current_difficulty:
            return DifficultyRecommendation(
                recommended_difficulty=target,
                current_difficulty=current_difficulty,
                direction="maintain",
                verdict=verdict,
                reasoning=(
                    "Readiness verdict was NOT_READY, indicating a significant competency gap, but this "
                    "scenario is already at the lowest difficulty ('easy'), so there is nowhere lower to "
                    "step down to. Recommend repeating practice at 'easy' before reattempting."
                ),
            )
        return DifficultyRecommendation(
            recommended_difficulty=target,
            current_difficulty=current_difficulty,
            direction="decrease",
            verdict=verdict,
            reasoning=(
                f"Readiness verdict was NOT_READY, indicating a significant competency gap. Recommend "
                f"stepping down from '{current_difficulty}' to '{target}' before attempting this scenario "
                f"again."
            ),
        )

    if verdict == "AT_RISK":
        return DifficultyRecommendation(
            recommended_difficulty=current_difficulty,
            current_difficulty=current_difficulty,
            direction="maintain",
            verdict=verdict,
            reasoning=(
                f"Readiness verdict was AT_RISK — a borderline miss, not a clear gap. Recommend staying at "
                f"'{current_difficulty}' for another attempt rather than changing difficulty in either "
                f"direction."
            ),
        )

    # verdict == "READY"
    narrowest_margin = min(r.score - r.min_score for r in results)
    if narrowest_margin >= READY_COMFORTABLE_MARGIN:
        target = _step(current_difficulty, +1)
        if target == current_difficulty:
            return DifficultyRecommendation(
                recommended_difficulty=target,
                current_difficulty=current_difficulty,
                direction="maintain",
                verdict=verdict,
                reasoning=(
                    f"Readiness verdict was READY with a comfortable margin (narrowest passing margin "
                    f"{narrowest_margin} points, at or above the {READY_COMFORTABLE_MARGIN}-point comfort "
                    f"threshold), but this scenario is already at the highest difficulty ('hard'), so there "
                    f"is nowhere higher to step up to."
                ),
            )
        return DifficultyRecommendation(
            recommended_difficulty=target,
            current_difficulty=current_difficulty,
            direction="increase",
            verdict=verdict,
            reasoning=(
                f"Readiness verdict was READY with a comfortable margin (narrowest passing margin "
                f"{narrowest_margin} points, at or above the {READY_COMFORTABLE_MARGIN}-point comfort "
                f"threshold). Recommend stepping up from '{current_difficulty}' to '{target}'."
            ),
        )

    return DifficultyRecommendation(
        recommended_difficulty=current_difficulty,
        current_difficulty=current_difficulty,
        direction="maintain",
        verdict=verdict,
        reasoning=(
            f"Readiness verdict was READY, but narrowly (narrowest passing margin {narrowest_margin} "
            f"points, below the {READY_COMFORTABLE_MARGIN}-point comfort threshold). Recommend staying at "
            f"'{current_difficulty}' to solidify performance before increasing difficulty."
        ),
    )
