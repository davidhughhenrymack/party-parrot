from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from beartype import beartype

from parrot_cloud.database import get_repo_root
from parrot_cloud.domain import FixtureSpec, SceneObjectSpec, VideoWallSpec

LEGACY_PLAN_UNITS_PER_METER = 50.0
FEET_PER_METER = 3.280839895
DJ_HEIGHT_METERS = 6.0 / FEET_PER_METER
DJ_TABLE_HEIGHT_METERS = 3.5 / FEET_PER_METER
DJ_TABLE_DEPTH_METERS = 4.0 / FEET_PER_METER
DJ_TABLE_WIDTH_METERS = 8.0 / FEET_PER_METER
DJ_SILHOUETTE_BEHIND_TABLE_EXTRA_M = 0.0
DJ_SILHOUETTE_CLEARANCE_BELOW_TABLE_TOP_M = 0.02


@beartype
@dataclass(frozen=True)
class SeedVenueDefinition:
    slug: str
    name: str
    active: bool
    archived: bool
    floor_width: float
    floor_depth: float
    floor_height: float
    manual_dimmer_supported: bool
    video_wall: VideoWallSpec
    scene_objects: tuple[SceneObjectSpec, ...]
    fixtures: tuple[FixtureSpec, ...]


def _fixture(
    fixture_id: str,
    fixture_type: str,
    address: int,
    universe: str,
    x: float,
    y: float,
    z: float,
    *,
    rotation_x: float = 0.0,
    rotation_y: float = 0.0,
    rotation_z: float = 0.0,
    name: str | None = None,
    group_name: str | None = None,
    is_manual: bool = False,
    options: dict[str, int | float | bool] | None = None,
) -> FixtureSpec:
    return FixtureSpec(
        id=fixture_id,
        fixture_type=fixture_type,
        address=address,
        universe=universe,
        x=x,
        y=y,
        z=z,
        rotation_x=rotation_x,
        rotation_y=rotation_y,
        rotation_z=rotation_z,
        name=name,
        group_name=group_name,
        is_manual=is_manual,
        options={} if options is None else dict(options),
    )


def _scene_object(
    scene_object_id: str,
    kind: str,
    x: float,
    y: float,
    z: float,
    *,
    width: float,
    height: float,
    depth: float,
    rotation_x: float = 0.0,
    rotation_y: float = 0.0,
    rotation_z: float = 0.0,
    locked: bool = False,
    options: dict[str, int | float | bool] | None = None,
) -> SceneObjectSpec:
    return SceneObjectSpec(
        id=scene_object_id,
        kind=kind,
        x=x,
        y=y,
        z=z,
        width=width,
        height=height,
        depth=depth,
        rotation_x=rotation_x,
        rotation_y=rotation_y,
        rotation_z=rotation_z,
        locked=locked,
        options={} if options is None else dict(options),
    )


LEGACY_FIXTURE_TYPE_MAP: dict[str, tuple[str, str | None, bool]] = {
    "sr-spot": ("manual_dimmer_channel", "SR spot", True),
    "sl-spot": ("manual_dimmer_channel", "SL spot", True),
    "chauvet-intimidator-120": ("chauvet_spot_110", None, False),
    "chauvet-intimidator-160": ("chauvet_spot_160", None, False),
    "led-par": ("par_rgb", None, False),
    "motionstrip-38": ("motionstrip_38", None, False),
    "oultia-2-beam-laser": ("two_beam_laser", None, False),
    "par-rgbawu": ("par_rgbawu", None, False),
}


def _load_mtn_lotus_gui() -> dict[str, dict[str, object]]:
    gui_path = Path(get_repo_root()) / "mtn_lotus_gui.json"
    return dict(json.loads(gui_path.read_text()))


def _legacy_orientation_to_euler_xyz(orientation: list[float]) -> tuple[float, float, float]:
    x, y, z, w = orientation

    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = _atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = _copysign(_pi_over_two(), sinp)
    else:
        pitch = _asin(sinp)

    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = _atan2(siny_cosp, cosy_cosp)
    return roll, pitch, yaw


def _atan2(y: float, x: float) -> float:
    import math
    return math.atan2(y, x)


def _asin(value: float) -> float:
    import math
    return math.asin(value)


def _copysign(value: float, sign: float) -> float:
    import math
    return math.copysign(value, sign)


def _pi_over_two() -> float:
    import math
    return math.pi / 2.0


def _build_mtn_lotus_fixtures() -> tuple[FixtureSpec, ...]:
    fixtures: list[FixtureSpec] = []
    legacy_floor_width = 450.0
    legacy_floor_depth = 400.0
    for legacy_id, pos_data in _load_mtn_lotus_gui().items():
        legacy_type, address_and_universe = legacy_id.split("@", 1)
        address_text, universe = address_and_universe.split(":", 1)
        mapped = LEGACY_FIXTURE_TYPE_MAP.get(legacy_type)
        if mapped is None:
            continue

        fixture_type, fixture_name, is_manual = mapped
        orientation = pos_data.get("orientation")
        rotation_x = 0.0
        rotation_y = 0.0
        rotation_z = 0.0
        if isinstance(orientation, list) and len(orientation) == 4:
            rotation_x, rotation_y, rotation_z = _legacy_orientation_to_euler_xyz(
                [float(value) for value in orientation]
            )

        fixture_id = (
            f"mtn-lotus-{legacy_type}-{address_text}-{universe}".replace("_", "-")
        )
        fixtures.append(
            _fixture(
                fixture_id,
                fixture_type,
                int(address_text),
                universe,
                (float(pos_data.get("x", 0.0)) - (legacy_floor_width / 2.0))
                / LEGACY_PLAN_UNITS_PER_METER,
                (float(pos_data.get("y", 0.0)) - (legacy_floor_depth / 2.0))
                / LEGACY_PLAN_UNITS_PER_METER,
                float(pos_data.get("z", 3.0)),
                rotation_x=rotation_x,
                rotation_y=rotation_y,
                rotation_z=rotation_z,
                name=fixture_name,
                is_manual=is_manual,
            )
        )

    fixtures.sort(key=lambda fixture: (fixture.universe, fixture.address))
    return tuple(fixtures)


def build_seed_venues() -> tuple[SeedVenueDefinition, ...]:
    floor_width = 450.0 / LEGACY_PLAN_UNITS_PER_METER
    floor_depth = 400.0 / LEGACY_PLAN_UNITS_PER_METER
    floor_height = 12.0
    table_width = DJ_TABLE_WIDTH_METERS
    table_depth = DJ_TABLE_DEPTH_METERS
    table_height = DJ_TABLE_HEIGHT_METERS
    table_y = -(floor_depth / 2.0) + 1.2
    video_wall = VideoWallSpec(
        x=0.0,
        y=-(floor_depth / 2.0) + 0.4,
        z=3.0,
        width=floor_width,
        height=6.0,
        depth=max(floor_depth * 0.025, 0.2),
        locked=False,
    )
    return (
        SeedVenueDefinition(
            slug="mtn-lotus-demo",
            name="Mountain Lotus Demo",
            active=True,
            archived=False,
            floor_width=floor_width,
            floor_depth=floor_depth,
            floor_height=floor_height,
            manual_dimmer_supported=True,
            video_wall=video_wall,
            scene_objects=(
                _scene_object(
                    "mtn-lotus-demo-floor",
                    "floor",
                    0.0,
                    0.0,
                    -0.04,
                    width=floor_width,
                    height=floor_depth,
                    depth=0.08,
                    options={"room_height": floor_height},
                ),
                _scene_object(
                    "mtn-lotus-demo-video-wall",
                    "video_wall",
                    video_wall.x,
                    video_wall.y,
                    video_wall.z,
                    width=video_wall.width,
                    height=video_wall.height,
                    depth=video_wall.depth,
                    locked=video_wall.locked,
                ),
                _scene_object(
                    "mtn-lotus-demo-dj-table",
                    "dj_table",
                    0.0,
                    table_y,
                    table_height / 2.0,
                    width=table_width,
                    height=table_height,
                    depth=table_depth,
                ),
                _scene_object(
                    "mtn-lotus-demo-dj-cutout",
                    "dj_cutout",
                    0.0,
                    table_y - table_depth / 2.0 - DJ_SILHOUETTE_BEHIND_TABLE_EXTRA_M,
                    table_height
                    + DJ_HEIGHT_METERS / 2.0
                    - DJ_SILHOUETTE_CLEARANCE_BELOW_TABLE_TOP_M,
                    width=0.9,
                    height=DJ_HEIGHT_METERS,
                    depth=0.05,
                    options={"use_billboard": True},
                ),
            ),
            fixtures=_build_mtn_lotus_fixtures(),
        ),
    )
