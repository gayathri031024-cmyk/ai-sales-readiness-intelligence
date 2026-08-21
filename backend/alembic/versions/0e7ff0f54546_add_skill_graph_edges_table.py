"""add skill_graph_edges table (Phase 14)

Revision ID: 0e7ff0f54546
Revises: ed1e90345d8b
Create Date: 2026-08-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e7ff0f54546'
down_revision: Union[str, None] = 'ed1e90345d8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('skill_graph_edges',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('from_competency_id', sa.String(length=36), nullable=False),
    sa.Column('to_competency_id', sa.String(length=36), nullable=False),
    sa.Column('relationship_type', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['from_competency_id'], ['competencies.id'], ),
    sa.ForeignKeyConstraint(['to_competency_id'], ['competencies.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('from_competency_id', 'to_competency_id'),
    )


def downgrade() -> None:
    op.drop_table('skill_graph_edges')
