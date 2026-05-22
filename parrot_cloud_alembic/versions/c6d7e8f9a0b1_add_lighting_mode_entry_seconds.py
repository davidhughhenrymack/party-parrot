"""add lighting mode entry seconds

Revision ID: c6d7e8f9a0b1
Revises: d5f6a7b8c9d0
Create Date: 2026-05-22 15:44:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6d7e8f9a0b1"
down_revision: Union[str, Sequence[str], None] = "d5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lighting_modes",
        sa.Column(
            "entry_seconds",
            sa.Float(),
            nullable=False,
            server_default="2.0",
        ),
    )
    op.execute("UPDATE lighting_modes SET entry_seconds = 3.0 WHERE key IN ('ethereal', 'chill')")
    op.execute("UPDATE lighting_modes SET entry_seconds = 0.5 WHERE key = 'rave'")
    op.execute("UPDATE lighting_modes SET entry_seconds = 0.1 WHERE key = 'stroby'")


def downgrade() -> None:
    op.drop_column("lighting_modes", "entry_seconds")
