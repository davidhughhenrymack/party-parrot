"""add lighting modes and animation assignments

Revision ID: d5f6a7b8c9d0
Revises: b4e2d6a8c9f0
Create Date: 2026-05-22 10:41:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "b4e2d6a8c9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lighting_modes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("venue_id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("editable", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("venue_id", "key", name="uq_lighting_modes_venue_key"),
    )
    op.create_index(op.f("ix_lighting_modes_key"), "lighting_modes", ["key"], unique=False)
    op.create_index(
        op.f("ix_lighting_modes_venue_id"),
        "lighting_modes",
        ["venue_id"],
        unique=False,
    )

    op.create_table(
        "venue_animation_assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("venue_id", sa.String(length=36), nullable=False),
        sa.Column("lighting_mode_id", sa.String(length=36), nullable=False),
        sa.Column("fixture_group_name", sa.String(length=255), nullable=True),
        sa.Column("fixture_type", sa.String(length=128), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("animation_spec", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["lighting_mode_id"], ["lighting_modes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_venue_animation_assignments_fixture_type"),
        "venue_animation_assignments",
        ["fixture_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_venue_animation_assignments_lighting_mode_id"),
        "venue_animation_assignments",
        ["lighting_mode_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_venue_animation_assignments_venue_id"),
        "venue_animation_assignments",
        ["venue_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_venue_animation_assignments_venue_id"),
        table_name="venue_animation_assignments",
    )
    op.drop_index(
        op.f("ix_venue_animation_assignments_lighting_mode_id"),
        table_name="venue_animation_assignments",
    )
    op.drop_index(
        op.f("ix_venue_animation_assignments_fixture_type"),
        table_name="venue_animation_assignments",
    )
    op.drop_table("venue_animation_assignments")
    op.drop_index(op.f("ix_lighting_modes_venue_id"), table_name="lighting_modes")
    op.drop_index(op.f("ix_lighting_modes_key"), table_name="lighting_modes")
    op.drop_table("lighting_modes")
