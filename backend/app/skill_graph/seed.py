"""
Seeds the MVP skill graph — a small, static, hand-authored set of
"depends_on" edges between the 3 competencies this MVP actually
evaluates (discovery, objection_handling, closing). Same posture and
same idempotency discipline as `scenario/service.py::seed_mvp_scenario`:
safe to call on every app startup, never creates duplicate edges.

Scoped only to competencies that actually exist in this MVP — the
full 7-competency graph MASTER_PROMPT.md names (Discovery, Pain
Identification, Product Knowledge, Value Articulation, Objection
Handling, Negotiation, Closing) is NOT built here, since 4 of those 7
have no `Competency` row, no threshold, and no evaluation data
anywhere in the MVP — building edges to/from them would be inventing
requirements no scenario or evaluation actually exercises. See
DECISIONS.md, Phase 14.

The graph itself — which competency depends on which — is a
documented judgment call, not derived from real transcript data
(same placeholder posture as `AT_RISK_MARGIN`/`READY_COMFORTABLE_MARGIN`):
Closing depends on both Discovery and Objection Handling (you can't
close well if you never understood the buyer's need or never handled
their objection); Objection Handling depends on Discovery (you can't
credibly handle an objection you don't understand the root of). This
directly matches MASTER_PROMPT.md's own example ("weak closing traced
back to weak discovery").
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Competency, SkillGraphEdge

# (from_key, to_key) — "from_key depends_on to_key"
_MVP_SKILL_GRAPH_EDGES: tuple[tuple[str, str], ...] = (
    ("closing", "discovery"),
    ("closing", "objection_handling"),
    ("objection_handling", "discovery"),
)

_RELATIONSHIP_TYPE = "depends_on"


def seed_mvp_skill_graph(db: Session) -> None:
    """Idempotent: only inserts an edge if it isn't already present.
    Requires the 3 MVP competencies to already exist — call this after
    `seed_mvp_scenario(db)`, never before (main.py's lifespan does
    this in order)."""
    competencies_by_key = {c.key: c for c in db.execute(select(Competency)).scalars().all()}

    existing_pairs = {
        (edge.from_competency_id, edge.to_competency_id)
        for edge in db.execute(select(SkillGraphEdge)).scalars().all()
    }

    for from_key, to_key in _MVP_SKILL_GRAPH_EDGES:
        from_competency = competencies_by_key.get(from_key)
        to_competency = competencies_by_key.get(to_key)
        if from_competency is None or to_competency is None:
            # Competencies not seeded yet (or a key was renamed) —
            # skip rather than crash; same "guard, don't fabricate"
            # posture as every other MVP seed function.
            continue

        pair = (from_competency.id, to_competency.id)
        if pair in existing_pairs:
            continue

        db.add(
            SkillGraphEdge(
                from_competency_id=from_competency.id,
                to_competency_id=to_competency.id,
                relationship_type=_RELATIONSHIP_TYPE,
            )
        )
        existing_pairs.add(pair)

    db.commit()
