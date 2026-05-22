"""add named positions

Revision ID: b4e2d6a8c9f0
Revises: f7c8d9e0a1b2
Create Date: 2026-05-22 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e2d6a8c9f0"
down_revision: Union[str, Sequence[str], None] = "f7c8d9e0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "named_positions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_named_positions_name"), "named_positions", ["name"], unique=True)

    op.create_table(
        "fixture_named_positions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("venue_id", sa.String(length=36), nullable=False),
        sa.Column("fixture_id", sa.String(length=36), nullable=False),
        sa.Column("named_position_id", sa.String(length=36), nullable=False),
        sa.Column("pan", sa.Float(), nullable=False),
        sa.Column("tilt", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["fixture_id"], ["fixtures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["named_position_id"], ["named_positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fixture_id",
            "named_position_id",
            name="uq_fixture_named_position_fixture_name",
        ),
    )
    op.create_index(
        op.f("ix_fixture_named_positions_fixture_id"),
        "fixture_named_positions",
        ["fixture_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fixture_named_positions_named_position_id"),
        "fixture_named_positions",
        ["named_position_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fixture_named_positions_venue_id"),
        "fixture_named_positions",
        ["venue_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO named_positions (id, name)
        VALUES ('00000000-0000-0000-0000-000000000001', 'Mirrorball')
        """
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_fixture_named_positions_venue_id"),
        table_name="fixture_named_positions",
    )
    op.drop_index(
        op.f("ix_fixture_named_positions_named_position_id"),
        table_name="fixture_named_positions",
    )
    op.drop_index(
        op.f("ix_fixture_named_positions_fixture_id"),
        table_name="fixture_named_positions",
    )
    op.drop_table("fixture_named_positions")
    op.drop_index(op.f("ix_named_positions_name"), table_name="named_positions")
    op.drop_table("named_positions")
