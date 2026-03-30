"""add scene objects table

Revision ID: 9f2f6d4a1b7c
Revises: c3a7b9f1d2e4
Create Date: 2026-03-30 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2f6d4a1b7c"
down_revision: Union[str, Sequence[str], None] = "c3a7b9f1d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scene_objects",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("venue_id", sa.String(length=36), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("z", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("depth", sa.Float(), nullable=False),
        sa.Column("rotation_x", sa.Float(), nullable=False),
        sa.Column("rotation_y", sa.Float(), nullable=False),
        sa.Column("rotation_z", sa.Float(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scene_objects_kind"), "scene_objects", ["kind"], unique=False
    )
    op.create_index(
        op.f("ix_scene_objects_venue_id"), "scene_objects", ["venue_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scene_objects_venue_id"), table_name="scene_objects")
    op.drop_index(op.f("ix_scene_objects_kind"), table_name="scene_objects")
    op.drop_table("scene_objects")
