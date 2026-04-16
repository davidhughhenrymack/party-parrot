from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from parrot_cloud.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class VenueModel(Base):
    __tablename__ = "venues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    floor_width: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    floor_depth: Mapped[float] = mapped_column(Float, nullable=False, default=15.0)
    floor_height: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    video_wall_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    video_wall_y: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    video_wall_z: Mapped[float] = mapped_column(Float, nullable=False, default=-4.5)
    video_wall_width: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    video_wall_height: Mapped[float] = mapped_column(Float, nullable=False, default=6.0)
    video_wall_depth: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    video_wall_locked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    manual_dimmer_supported: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    fixtures: Mapped[list["FixtureModel"]] = relationship(
        back_populates="venue",
        cascade="all, delete-orphan",
        order_by="FixtureModel.order_index",
    )
    scene_objects: Mapped[list["SceneObjectModel"]] = relationship(
        back_populates="venue",
        cascade="all, delete-orphan",
        order_by="SceneObjectModel.order_index",
    )


class FixtureModel(Base):
    __tablename__ = "fixtures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    venue_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fixture_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    address: Mapped[int] = mapped_column(Integer, nullable=False)
    universe: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    z: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rotation_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rotation_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rotation_z: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    options: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    venue: Mapped[VenueModel] = relationship(back_populates="fixtures")


class SceneObjectModel(Base):
    __tablename__ = "scene_objects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    venue_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    z: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    depth: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    rotation_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rotation_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rotation_z: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    options: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    venue: Mapped[VenueModel] = relationship(back_populates="scene_objects")


class ControlStateModel(Base):
    __tablename__ = "control_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    mode: Mapped[str] = mapped_column(String(64), nullable=False, default="chill")
    vj_mode: Mapped[str] = mapped_column(
        String(64), nullable=False, default="prom_dmack"
    )
    theme_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Rave")
    active_venue_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    display_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="dmx_heatmap"
    )
    manual_dimmer: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hype_limiter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    show_waveform: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_fixture_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
