"""add lighting mode hotkey

Revision ID: f1a2b3c4d5e6
Revises: c6d7e8f9a0b1
Create Date: 2026-05-26 15:16:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "c6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lighting_modes", sa.Column("hotkey", sa.String(length=1), nullable=True))


def downgrade() -> None:
    op.drop_column("lighting_modes", "hotkey")
