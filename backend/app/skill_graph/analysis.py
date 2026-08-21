"""
Deterministic root-cause analysis (Phase 14).

Pure Python — no LLM, no DB session, no import from `app.ai` at all,
same module-boundary discipline `readiness/decision.py` and
`difficulty/decision.py` establish and this file's own tests enforce
directly (its functions take no provider parameter at all).

MASTER_PROMPT.md's COMPETENCY / SKILL GRAPH section: "The system may
propose root causes (e.g., weak closing traced back to weak
discovery) but must not claim causality without evidence." This
module never claims causality — it identifies a *correlation within
this one conversation* (both competencies fell short here) and
surfaces it with the upstream competency's own already-verified
diagnosis text as the evidence for that correlation, in deliberately
hedged language ("may be a contributing factor"). One conversation's
data can never prove causation on its own; the wording reflects that
honestly rather than overclaiming.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.readiness.decision import CompetencyResult


@dataclass(frozen=True)
class SkillGraphEdgeInfo:
    """Already-resolved input — a real edge from the persisted skill
    graph, reduced to the two competency keys it connects. This
    function only ever compares data already handed to it; it never
    looks anything up itself."""

    from_competency_key: str
    to_competency_key: str


@dataclass(frozen=True)
class RelatedWeakness:
    competency_key: str
    display_name: str
    reason: str


def find_related_weaknesses(
    results: list[CompetencyResult],
    diagnoses_by_key: dict[str, str],
    edges: list[SkillGraphEdgeInfo],
) -> dict[str, list[RelatedWeakness]]:
    """For each competency that failed its threshold in this
    conversation, look at its outgoing "depends_on" edges. If an
    upstream competency it depends on ALSO failed in this same
    conversation, record it as a possible contributing factor,
    quoting that upstream competency's own already-verified (Phase 8)
    diagnosis text as the evidence.

    A competency that failed but has no failing upstream dependency
    (or no edges at all) is simply absent from the returned dict —
    there is no correlation to surface, not an error.
    """
    failing_keys = {r.competency_key for r in results if not r.passed}
    display_names = {r.competency_key: r.display_name for r in results}

    edges_by_from: dict[str, list[SkillGraphEdgeInfo]] = {}
    for edge in edges:
        edges_by_from.setdefault(edge.from_competency_key, []).append(edge)

    related: dict[str, list[RelatedWeakness]] = {}
    for key in failing_keys:
        candidates: list[RelatedWeakness] = []
        for edge in edges_by_from.get(key, []):
            upstream_key = edge.to_competency_key
            if upstream_key in failing_keys and upstream_key in diagnoses_by_key:
                upstream_display = display_names.get(upstream_key, upstream_key)
                candidates.append(
                    RelatedWeakness(
                        competency_key=upstream_key,
                        display_name=upstream_display,
                        reason=(
                            f"{upstream_display} also fell short of its threshold in this "
                            f"conversation and may be a contributing factor: "
                            f"{diagnoses_by_key[upstream_key]}"
                        ),
                    )
                )
        if candidates:
            related[key] = candidates

    return related
