"""add display mode and active venue to control state

Revision ID: a1d9c4e7f2b3
Revises: 9f2f6d4a1b7c
Create Date: 2026-04-16 10:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1d9c4e7f2b3"
down_revision: Union[str, Sequence[str], None] = "9f2f6d4a1b7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "control_state",
        sa.Column("active_venue_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "control_state",
        sa.Column(
            "display_mode",
            sa.String(length=32),
            nullable=False,
            server_default="dmx_heatmap",
        ),
    )
    op.execute(
        """
        UPDATE control_state
        SET active_venue_id = (
            SELECT id
            FROM venues
            WHERE active = 1
            ORDER BY updated_at DESC
            LIMIT 1
        )
        """
    )
    op.execute(
        """
        UPDATE control_state
        SET display_mode = CASE
            WHEN show_fixture_mode = 1 THEN 'venue'
            ELSE 'dmx_heatmap'
        END
        """
    )


def downgrade() -> None:
    op.drop_column("control_state", "display_mode")
    op.drop_column("control_state", "active_venue_id")
