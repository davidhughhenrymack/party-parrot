"""add manual_fixture_dimmers json to control_state

Revision ID: e8b2c1d4f5a6
Revises: a1d9c4e7f2b3
Create Date: 2026-04-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8b2c1d4f5a6"
down_revision: Union[str, Sequence[str], None] = "a1d9c4e7f2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "control_state",
        sa.Column(
            "manual_fixture_dimmers",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("control_state", "manual_fixture_dimmers")
