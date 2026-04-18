from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from beartype import beartype

from parrot_cloud.domain import FixtureSpec, SceneObjectSpec, VideoWallSpec

# Legacy plan units (pre-DB editor) used 50 units per meter. Kept for reference.
LEGACY_PLAN_UNITS_PER_METER = 50.0
FEET_PER_METER = 3.280839895
DJ_HEIGHT_METERS = 6.0 / FEET_PER_METER
DJ_TABLE_HEIGHT_METERS = 3.5 / FEET_PER_METER
DJ_TABLE_DEPTH_METERS = 4.0 / FEET_PER_METER
DJ_TABLE_WIDTH_METERS = 8.0 / FEET_PER_METER
DJ_SILHOUETTE_BEHIND_TABLE_EXTRA_M = 0.0
DJ_SILHOUETTE_CLEARANCE_BELOW_TABLE_TOP_M = 0.08


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
    options: dict[str, Any] | None = None,
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


def build_seed_venues() -> tuple[SeedVenueDefinition, ...]:
    """First-run demo venue shell.

    The mtn_lotus_gui.json fixture import is gone — venues are edited in the
    cloud editor now. We still seed an empty ``mtn-lotus-demo`` venue on first
    boot so the app has an active venue to render (floor + DJ table + video
    wall), and ``ensure_seed_data`` has something idempotent to re-apply.
    """
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
            fixtures=(),
        ),
    )
