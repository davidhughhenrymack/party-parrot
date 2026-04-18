from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from beartype import beartype


JsonDict = dict[str, Any]


@beartype
@dataclass(frozen=True)
class VenueSummary:
    id: str
    slug: str
    name: str
    archived: bool
    active: bool
    revision: int

    def to_dict(self) -> JsonDict:
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "archived": self.archived,
            "active": self.active,
            "revision": self.revision,
        }

    @classmethod
    def from_dict(cls, data: JsonDict) -> "VenueSummary":
        return cls(
            id=str(data["id"]),
            slug=str(data["slug"]),
            name=str(data["name"]),
            archived=bool(data.get("archived", False)),
            active=bool(data.get("active", False)),
            revision=int(data.get("revision", 0)),
        )


@beartype
@dataclass(frozen=True)
class VideoWallSpec:
    x: float
    y: float
    z: float
    width: float
    height: float
    depth: float
    locked: bool

    def to_dict(self) -> JsonDict:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
            "locked": self.locked,
        }

    @classmethod
    def from_dict(cls, data: JsonDict) -> "VideoWallSpec":
        return cls(
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            z=float(data.get("z", 0.0)),
            width=float(data.get("width", 10.0)),
            height=float(data.get("height", 6.0)),
            depth=float(data.get("depth", 0.25)),
            locked=bool(data.get("locked", False)),
        )


@beartype
@dataclass(frozen=True)
class SceneObjectSpec:
    id: str
    kind: str
    x: float
    y: float
    z: float
    width: float
    height: float
    depth: float
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    locked: bool = False
    options: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "id": self.id,
            "kind": self.kind,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
            "rotation_x": self.rotation_x,
            "rotation_y": self.rotation_y,
            "rotation_z": self.rotation_z,
            "locked": self.locked,
            "options": dict(self.options),
        }

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SceneObjectSpec":
        return cls(
            id=str(data["id"]),
            kind=str(data["kind"]),
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            z=float(data.get("z", 0.0)),
            width=float(data.get("width", 1.0)),
            height=float(data.get("height", 1.0)),
            depth=float(data.get("depth", 1.0)),
            rotation_x=float(data.get("rotation_x", 0.0)),
            rotation_y=float(data.get("rotation_y", 0.0)),
            rotation_z=float(data.get("rotation_z", 0.0)),
            locked=bool(data.get("locked", False)),
            options=dict(data.get("options", {})),
        )


@beartype
@dataclass(frozen=True)
class FixtureSpec:
    id: str
    fixture_type: str
    address: int
    universe: str
    x: float
    y: float
    z: float
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    name: str | None = None
    group_name: str | None = None
    is_manual: bool = False
    options: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "id": self.id,
            "fixture_type": self.fixture_type,
            "address": self.address,
            "universe": self.universe,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "rotation_x": self.rotation_x,
            "rotation_y": self.rotation_y,
            "rotation_z": self.rotation_z,
            "name": self.name,
            "group_name": self.group_name,
            "is_manual": self.is_manual,
            "options": dict(self.options),
        }

    @classmethod
    def from_dict(cls, data: JsonDict) -> "FixtureSpec":
        return cls(
            id=str(data["id"]),
            fixture_type=str(data["fixture_type"]),
            address=int(data["address"]),
            universe=str(data.get("universe", "default")),
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            z=float(data.get("z", 0.0)),
            rotation_x=float(data.get("rotation_x", 0.0)),
            rotation_y=float(data.get("rotation_y", 0.0)),
            rotation_z=float(data.get("rotation_z", 0.0)),
            name=data.get("name"),
            group_name=data.get("group_name"),
            is_manual=bool(data.get("is_manual", False)),
            options=dict(data.get("options", {})),
        )


@beartype
@dataclass(frozen=True)
class VenueSnapshot:
    summary: VenueSummary
    floor_width: float
    floor_depth: float
    floor_height: float
    video_wall: VideoWallSpec
    fixtures: tuple[FixtureSpec, ...]
    scene_objects: tuple[SceneObjectSpec, ...] = field(default_factory=tuple)

    def to_dict(self) -> JsonDict:
        return {
            "summary": self.summary.to_dict(),
            "floor_width": self.floor_width,
            "floor_depth": self.floor_depth,
            "floor_height": self.floor_height,
            "video_wall": self.video_wall.to_dict(),
            "fixtures": [fixture.to_dict() for fixture in self.fixtures],
            "scene_objects": [scene_object.to_dict() for scene_object in self.scene_objects],
        }

    @classmethod
    def from_dict(cls, data: JsonDict) -> "VenueSnapshot":
        return cls(
            summary=VenueSummary.from_dict(dict(data["summary"])),
            floor_width=float(data.get("floor_width", 20.0)),
            floor_depth=float(data.get("floor_depth", 15.0)),
            floor_height=float(data.get("floor_height", 10.0)),
            video_wall=VideoWallSpec.from_dict(dict(data.get("video_wall", {}))),
            fixtures=tuple(
                FixtureSpec.from_dict(dict(fixture_data))
                for fixture_data in data.get("fixtures", [])
            ),
            scene_objects=tuple(
                SceneObjectSpec.from_dict(dict(scene_object_data))
                for scene_object_data in data.get("scene_objects", [])
            ),
        )

    def scene_object(self, kind: str) -> SceneObjectSpec | None:
        return next(
            (scene_object for scene_object in self.scene_objects if scene_object.kind == kind),
            None,
        )


@beartype
@dataclass(frozen=True)
class ControlState:
    mode: str
    vj_mode: str
    theme_name: str
    active_venue_id: str | None
    display_mode: str
    manual_dimmer: float
    hype_limiter: bool
    show_waveform: bool

    def to_dict(self) -> JsonDict:
        return {
            "mode": self.mode,
            "vj_mode": self.vj_mode,
            "theme_name": self.theme_name,
            "active_venue_id": self.active_venue_id,
            "display_mode": self.display_mode,
            "manual_dimmer": self.manual_dimmer,
            "hype_limiter": self.hype_limiter,
            "show_waveform": self.show_waveform,
        }

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ControlState":
        return cls(
            mode=str(data.get("mode", "chill")),
            vj_mode=str(data.get("vj_mode", "prom_dmack")),
            theme_name=str(data.get("theme_name", "Rave")),
            active_venue_id=(
                str(data.get("active_venue_id"))
                if data.get("active_venue_id") not in (None, "")
                else None
            ),
            display_mode=str(
                data.get(
                    "display_mode",
                    "venue" if bool(data.get("show_fixture_mode", False)) else "dmx_heatmap",
                )
            ),
            manual_dimmer=float(data.get("manual_dimmer", 0.0)),
            hype_limiter=bool(data.get("hype_limiter", False)),
            show_waveform=bool(data.get("show_waveform", True)),
        )


@beartype
@dataclass(frozen=True)
class RuntimeBootstrap:
    venues: tuple[VenueSummary, ...]
    active_venue: VenueSnapshot | None
    control_state: ControlState
    fixture_runtime_state: JsonDict = field(
        default_factory=lambda: {"version": 1, "fixtures": []}
    )
    vj_preview: JsonDict | None = None

    def to_dict(self) -> JsonDict:
        return {
            "venues": [venue.to_dict() for venue in self.venues],
            "active_venue": (
                None if self.active_venue is None else self.active_venue.to_dict()
            ),
            "control_state": self.control_state.to_dict(),
            "fixture_runtime_state": dict(self.fixture_runtime_state),
            "vj_preview": (
                None if self.vj_preview is None else dict(self.vj_preview)
            ),
        }

    @classmethod
    def from_dict(cls, data: JsonDict) -> "RuntimeBootstrap":
        active_venue_data = data.get("active_venue")
        frs = data.get("fixture_runtime_state")
        if not isinstance(frs, dict):
            frs = {"version": 1, "fixtures": []}
        vp = data.get("vj_preview")
        if vp is not None and not isinstance(vp, dict):
            vp = None
        return cls(
            venues=tuple(
                VenueSummary.from_dict(dict(venue_data))
                for venue_data in data.get("venues", [])
            ),
            active_venue=(
                None
                if active_venue_data is None
                else VenueSnapshot.from_dict(dict(active_venue_data))
            ),
            control_state=ControlState.from_dict(dict(data.get("control_state", {}))),
            fixture_runtime_state=dict(frs),
            vj_preview=dict(vp) if vp is not None else None,
        )
