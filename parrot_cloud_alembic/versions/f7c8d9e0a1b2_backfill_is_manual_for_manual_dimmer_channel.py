"""backfill is_manual for manual_dimmer_channel fixtures

Revision ID: f7c8d9e0a1b2
Revises: e8b2c1d4f5a6
Create Date: 2026-04-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f7c8d9e0a1b2"
down_revision: Union[str, Sequence[str], None] = "e8b2c1d4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE fixtures
        SET is_manual = 1
        WHERE fixture_type = 'manual_dimmer_channel' AND is_manual = 0
        """
    )


def downgrade() -> None:
    pass
