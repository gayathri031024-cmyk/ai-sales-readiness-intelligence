"""Seed MVP Enterprise CFO scenario.

Revision ID: 1a2b3c4d5e6f
Revises: 0e7ff0f54546
"""

from typing import Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "0e7ff0f54546"
branch_labels = None
depends_on = None


PERSONA_ID = "11111111-1111-1111-1111-111111111111"
SCENARIO_ID = "22222222-2222-2222-2222-222222222222"

DISCOVERY_ID = "33333333-3333-3333-3333-333333333333"
OBJECTION_ID = "44444444-4444-4444-4444-444444444444"
CLOSING_ID = "55555555-5555-5555-5555-555555555555"


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    existing = bind.execute(
        sa.text("SELECT id FROM scenarios WHERE id = :id"),
        {"id": SCENARIO_ID},
    ).first()

    if existing is not None:
        return

    bind.execute(
        sa.text(
            """
            INSERT INTO buyer_personas
                (id, name, description, base_state, created_at)
            VALUES
                (:id, :name, :description, :base_state, :created_at)
            """
        ),
        {
            "id": PERSONA_ID,
            "name": "Enterprise CFO",
            "description": (
                "High sophistication. Primary concern is ROI and "
                "budget-cycle risk. Will raise a pricing objection early "
                "and push back on vague answers."
            ),
            "base_state": (
                '{"trust": 45, "patience": 60, '
                '"budget_sensitivity": 80, "interest": 55}'
            ),
            "created_at": now,
        },
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO scenarios
                (
                    id,
                    title,
                    buyer_persona_id,
                    product_context,
                    known_objection,
                    difficulty,
                    max_turns,
                    created_at
                )
            VALUES
                (
                    :id,
                    :title,
                    :buyer_persona_id,
                    :product_context,
                    :known_objection,
                    :difficulty,
                    :max_turns,
                    :created_at
                )
            """
        ),
        {
            "id": SCENARIO_ID,
            "title": "Enterprise CFO — Price Objection",
            "buyer_persona_id": PERSONA_ID,
            "product_context": (
                "AI-powered CRM platform, positioned against Salesforce "
                "for a 400-seat enterprise deal."
            ),
            "known_objection": (
                "Price — currently evaluating a cheaper competitor."
            ),
            "difficulty": "standard",
            "max_turns": 12,
            "created_at": now,
        },
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO competencies
                (id, key, display_name)
            VALUES
                (:discovery_id, 'discovery', 'Discovery'),
                (:objection_id, 'objection_handling', 'Objection Handling'),
                (:closing_id, 'closing', 'Closing')
            """
        ),
        {
            "discovery_id": DISCOVERY_ID,
            "objection_id": OBJECTION_ID,
            "closing_id": CLOSING_ID,
        },
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO scenario_competency_thresholds
                (scenario_id, competency_id, min_score)
            VALUES
                (:scenario_id, :discovery_id, 60),
                (:scenario_id, :objection_id, 70),
                (:scenario_id, :closing_id, 65)
            """
        ),
        {
            "scenario_id": SCENARIO_ID,
            "discovery_id": DISCOVERY_ID,
            "objection_id": OBJECTION_ID,
            "closing_id": CLOSING_ID,
        },
    )


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            DELETE FROM scenario_competency_thresholds
            WHERE scenario_id = :scenario_id
            """
        ),
        {"scenario_id": SCENARIO_ID},
    )

    bind.execute(
        sa.text(
            """
            DELETE FROM scenarios
            WHERE id = :scenario_id
            """
        ),
        {"scenario_id": SCENARIO_ID},
    )

    bind.execute(
        sa.text(
            """
            DELETE FROM buyer_personas
            WHERE id = :persona_id
            """
        ),
        {"persona_id": PERSONA_ID},
    )

    bind.execute(
        sa.text(
            """
            DELETE FROM competencies
            WHERE id IN (:discovery_id, :objection_id, :closing_id)
            """
        ),
        {
            "discovery_id": DISCOVERY_ID,
            "objection_id": OBJECTION_ID,
            "closing_id": CLOSING_ID,
        },
    )