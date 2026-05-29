"""add animation fixture index filter

Revision ID: a9b8c7d6e5f4
Revises: f1a2b3c4d5e6
Create Date: 2026-05-29 14:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "venue_animation_assignments",
        sa.Column("fixture_index_filter", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("venue_animation_assignments", "fixture_index_filter")
