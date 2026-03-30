"""add control state table

Revision ID: c3a7b9f1d2e4
Revises: 1173a48cf4c7
Create Date: 2026-03-30 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3a7b9f1d2e4"
down_revision: Union[str, Sequence[str], None] = "1173a48cf4c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "control_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column("vj_mode", sa.String(length=64), nullable=False),
        sa.Column("theme_name", sa.String(length=255), nullable=False),
        sa.Column("manual_dimmer", sa.Float(), nullable=False),
        sa.Column("hype_limiter", sa.Boolean(), nullable=False),
        sa.Column("show_waveform", sa.Boolean(), nullable=False),
        sa.Column("show_fixture_mode", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("control_state")
