from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
import time
import uuid

from beartype import beartype
from sqlalchemy import select
from sqlalchemy.orm import object_session

from parrot_cloud.domain import (
    ControlState,
    FixtureNamedPositionSpec,
    FixtureSpec,
    LightingModeSpec,
    NamedPositionSpec,
    RuntimeBootstrap,
    SceneObjectSpec,
    VenueAnimationAssignmentSpec,
    VenueSnapshot,
    VenueSummary,
    VideoWallSpec,
)
from parrot_cloud.models import (
    ControlStateModel,
    FixtureNamedPositionModel,
    FixtureModel,
    LightingModeModel,
    NamedPositionModel,
    SceneObjectModel,
    VenueAnimationAssignmentModel,
    VenueModel,
)
from parrot_cloud.database import create_session
from parrot_cloud.fixture_catalog import (
    dmx_address_width_for_fixture,
    fixture_type_has_pan_tilt_range,
    pan_tilt_range_default_options,
)
from parrot_cloud.fixture_type_aliases import normalize_fixture_type_key
from parrot_cloud.seeds import SeedVenueDefinition, build_seed_venues
from parrot.utils.dmx_utils import Universe
from parrot.vj.vj_mode import parse_vj_mode_string
from parrot.director.animation_registry import (
    DEFAULT_MOVING_LIGHT_ANIMATION,
    DEFAULT_PAR_ANIMATION,
    DEFAULT_STROBY_MOVING_LIGHT_ANIMATION,
    DEFAULT_STROBY_PAR_ANIMATION,
)

LEGACY_PLAN_UNITS_PER_METER = 50.0
DJ_HEIGHT_METERS = 1.8288
DJ_TABLE_HEIGHT_METERS = 1.0668
DJ_TABLE_DEPTH_METERS = 1.2192
DJ_TABLE_WIDTH_METERS = 2.4384
# Silhouette is centered on the DJ table’s upstage edge; extra meters further upstage (optional).
DJ_SILHOUETTE_BEHIND_TABLE_EXTRA_M = 0.0
DJ_SILHOUETTE_CLEARANCE_BELOW_TABLE_TOP_M = 0.08
DISPLAY_MODE_VALUES = {"venue", "dmx_heatmap", "vj"}
DEFAULT_EDITABLE_LIGHTING_MODES: tuple[tuple[str, str], ...] = (
    ("chill", "Chill"),
    ("rave", "Rave"),
    ("stroby", "Stroby"),
)
DEFAULT_LIGHTING_MODE_ENTRY_SECONDS: dict[str, float] = {
    "ethereal": 3.0,
    "chill": 3.0,
    "rave": 0.5,
    "stroby": 0.1,
}
DEFAULT_LIGHTING_MODE_ANIMATION_ROWS = {
    "chill": (
        ("par", DEFAULT_PAR_ANIMATION),
        ("moving_head", DEFAULT_MOVING_LIGHT_ANIMATION),
    ),
    "rave": (
        ("par", DEFAULT_PAR_ANIMATION),
        ("moving_head", DEFAULT_MOVING_LIGHT_ANIMATION),
    ),
    "stroby": (
        ("par", DEFAULT_STROBY_PAR_ANIMATION),
        ("moving_head", DEFAULT_STROBY_MOVING_LIGHT_ANIMATION),
    ),
}
UTILITY_LIGHTING_MODE_KEYS: tuple[str, ...] = ("test", "blackout", "home")


def _is_manual_dimmer_channel_type(fixture_type: str) -> bool:
    return fixture_type == "manual_dimmer_channel"


# Top-level fields that PATCH/POST may send for the mechanical pan/tilt range of a
# moving head. They're stored inside `FixtureModel.options` (a JSON column) alongside
# position and rotation on the same row, so no schema migration is required.
_PAN_TILT_RANGE_FIELDS: tuple[str, ...] = (
    "pan_lower",
    "pan_upper",
    "tilt_lower",
    "tilt_upper",
)


def _normalize_named_position_name(value: object) -> str:
    name = str(value).strip()
    if not name:
        raise ValueError("Named position name cannot be empty")
    return name


def _normalize_lighting_mode_key(value: object) -> str:
    key = str(value).strip().lower().replace(" ", "_")
    if not key:
        raise ValueError("Lighting mode key cannot be empty")
    if key in UTILITY_LIGHTING_MODE_KEYS:
        raise ValueError(f"Lighting mode {key!r} is fixed and cannot be edited")
    return key


def _lighting_mode_label_from_key(key: str) -> str:
    return key.replace("_", " ").title()


def _lighting_mode_entry_seconds_from_key(key: str) -> float:
    return DEFAULT_LIGHTING_MODE_ENTRY_SECONDS.get(key, 2.0)


def _normalize_entry_seconds(value: object) -> float:
    return max(0.05, float(value))


def _clamp_dmx_float(value: object) -> float:
    return max(0.0, min(255.0, float(value)))


def _extract_pan_tilt_range(data: dict[str, object]) -> dict[str, float]:
    """Return any pan/tilt range fields present at the top level of `data`."""
    return {
        key: float(data[key])  # type: ignore[arg-type]
        for key in _PAN_TILT_RANGE_FIELDS
        if key in data
    }


def _hydrate_pan_tilt_range(
    fixture_type: str,
    stored_options: dict[str, object],
) -> dict[str, object]:
    """Return ``stored_options`` with any missing pan/tilt range keys filled.

    Moving heads created before pan/tilt range defaults were introduced carry an
    ``options`` blob that doesn't include these four keys, which caused the
    venue editor UI to show all-zero ranges. On read we fill any missing key
    from the type's :func:`pan_tilt_range_default_options`, so the editor and
    runtime always see sensible bounds. This is a pure read-side hydration —
    the DB row stays untouched until the user actually edits a field.
    """
    if not fixture_type_has_pan_tilt_range(fixture_type):
        return stored_options
    defaults = pan_tilt_range_default_options(fixture_type)
    hydrated = dict(stored_options)
    for key, default_value in defaults.items():
        if key not in hydrated:
            hydrated[key] = default_value
    return hydrated


def _merge_pan_tilt_range_into_options(
    existing_options: dict[str, object],
    explicit_options: dict[str, object] | None,
    range_overrides: dict[str, float],
) -> dict[str, object]:
    """Build the new `options` dict for a fixture update.

    If the caller sent a top-level ``options`` key, it replaces the existing dict
    wholesale (legacy behavior). Any top-level pan/tilt range fields are then
    merged on top, so the editor can change a single field without having to
    resend the entire options blob.
    """
    base: dict[str, object] = (
        dict(explicit_options) if explicit_options is not None else dict(existing_options)
    )
    base.update(range_overrides)
    return base


@contextmanager
def _session_scope():
    session = create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _slugify(name: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or f"venue-{uuid.uuid4().hex[:8]}"


def _normalize_universe(value: object) -> str:
    if value in (None, ""):
        return Universe.default.value
    universe_value = str(value)
    try:
        return Universe(universe_value).value
    except ValueError as exc:
        raise ValueError(f"Unsupported universe: {universe_value}") from exc


STANDARD_SCENE_OBJECT_ORDER = (
    "floor",
    "video_wall",
    "dj_table",
    "dj_cutout",
)


@beartype
class VenueRepository:
    def __init__(self) -> None:
        self._fixture_runtime_state: dict[str, object] = {"version": 1, "fixtures": []}
        self._runtime_interpretation_tree: dict[str, object] = {
            "version": 1,
            "updated_at": None,
            "mode": None,
            "tree": {
                "kind": "mode",
                "label": "No interpretation available",
                "children": [],
            },
        }
        self._vj_preview_jpeg: bytes | None = None
        self._vj_preview_updated_at: float | None = None

    def get_fixture_runtime_state(self) -> dict[str, object]:
        return dict(self._fixture_runtime_state)

    def get_runtime_interpretation_tree(self) -> dict[str, object]:
        return dict(self._runtime_interpretation_tree)

    def set_runtime_interpretation_tree(
        self, data: dict[str, object]
    ) -> dict[str, object]:
        tree = data.get("tree")
        if not isinstance(tree, dict):
            raise ValueError("Interpretation payload must include a tree object")
        payload = {
            "version": int(data.get("version", 1)),
            "updated_at": float(data.get("updated_at", time.time())),
            "mode": str(data.get("mode", "")),
            "tree": dict(tree),
        }
        self._runtime_interpretation_tree = payload
        return self.get_runtime_interpretation_tree()

    def set_fixture_runtime_state(self, data: dict[str, object]) -> dict[str, object]:
        version = int(data.get("version", 1))
        fixtures_raw = data.get("fixtures", [])
        if not isinstance(fixtures_raw, list):
            fixtures_raw = []
        normalized: list[dict[str, object]] = []
        for item in fixtures_raw:
            if not isinstance(item, dict) or item.get("id") is None:
                continue
            entry: dict[str, object] = {"id": str(item["id"])}
            if "dimmer" in item:
                entry["dimmer"] = float(max(0.0, min(1.0, float(item["dimmer"]))))
            if "rgb" in item and isinstance(item["rgb"], list) and len(item["rgb"]) >= 3:
                rgb = item["rgb"]
                entry["rgb"] = [
                    float(max(0.0, min(1.0, float(rgb[0])))),
                    float(max(0.0, min(1.0, float(rgb[1])))),
                    float(max(0.0, min(1.0, float(rgb[2])))),
                ]
            if "strobe" in item and item["strobe"] is not None:
                entry["strobe"] = float(max(0.0, min(1.0, float(item["strobe"]))))
            if "focus" in item and item["focus"] is not None:
                entry["focus"] = float(max(0.0, min(1.0, float(item["focus"]))))
            for key in ("pan_deg", "tilt_deg", "bar_pan_deg"):
                if key in item and item[key] is not None:
                    entry[key] = float(item[key])
            if "prism_on" in item and item["prism_on"] is not None:
                entry["prism_on"] = bool(item["prism_on"])
            if "prism_rotate_speed" in item and item["prism_rotate_speed"] is not None:
                speed = float(item["prism_rotate_speed"])
                entry["prism_rotate_speed"] = max(-1.0, min(1.0, speed))
            bulbs_raw = item.get("bulbs")
            if isinstance(bulbs_raw, list):
                bulbs: list[dict[str, object]] = []
                for bulb in bulbs_raw:
                    if not isinstance(bulb, dict):
                        continue
                    b: dict[str, object] = {}
                    if "dimmer" in bulb:
                        b["dimmer"] = float(max(0.0, min(1.0, float(bulb["dimmer"]))))
                    if "rgb" in bulb and isinstance(bulb["rgb"], list) and len(bulb["rgb"]) >= 3:
                        br = bulb["rgb"]
                        b["rgb"] = [
                            float(max(0.0, min(1.0, float(br[0])))),
                            float(max(0.0, min(1.0, float(br[1])))),
                            float(max(0.0, min(1.0, float(br[2])))),
                        ]
                    if "strobe" in bulb and bulb["strobe"] is not None:
                        b["strobe"] = float(max(0.0, min(1.0, float(bulb["strobe"]))))
                    if b:
                        bulbs.append(b)
                if bulbs:
                    entry["bulbs"] = bulbs
            normalized.append(entry)
        out: dict[str, object] = {"version": version, "fixtures": normalized}
        palette_raw = data.get("color_palette")
        if isinstance(palette_raw, list) and len(palette_raw) == 3:
            triple: list[list[float]] = []
            for slot in palette_raw:
                if not isinstance(slot, list) or len(slot) < 3:
                    triple = []
                    break
                triple.append(
                    [
                        float(max(0.0, min(1.0, float(slot[0])))),
                        float(max(0.0, min(1.0, float(slot[1])))),
                        float(max(0.0, min(1.0, float(slot[2])))),
                    ]
                )
            if len(triple) == 3:
                out["color_palette"] = triple
        self._fixture_runtime_state = out
        return self.get_fixture_runtime_state()

    def get_vj_preview_jpeg(self) -> bytes | None:
        return self._vj_preview_jpeg

    def set_vj_preview_jpeg(self, data: bytes) -> dict[str, object]:
        if len(data) > 5 * 1024 * 1024:
            raise ValueError("VJ preview image too large")
        if len(data) < 3 or data[0:3] != b"\xff\xd8\xff":
            raise ValueError("VJ preview must be a JPEG")
        self._vj_preview_jpeg = bytes(data)
        self._vj_preview_updated_at = time.time()
        return {"updated_at": float(self._vj_preview_updated_at)}

    def list_venue_summaries(self) -> list[VenueSummary]:
        with _session_scope() as session:
            venues = session.scalars(select(VenueModel).order_by(VenueModel.name)).all()
            return [self._summary_from_model(venue) for venue in venues]

    def get_runtime_bootstrap(self) -> RuntimeBootstrap:
        venues = tuple(self.list_venue_summaries())
        active_venue = self.get_active_venue_snapshot()
        control_state = self.get_control_state()
        vj_blob = self._vj_preview_jpeg
        vj_ts = self._vj_preview_updated_at
        vj_preview = (
            None
            if vj_blob is None or vj_ts is None
            else {"updated_at": float(vj_ts)}
        )
        return RuntimeBootstrap(
            venues=venues,
            active_venue=active_venue,
            control_state=control_state,
            fixture_runtime_state=self.get_fixture_runtime_state(),
            vj_preview=vj_preview,
        )

    def get_control_state(self) -> ControlState:
        with _session_scope() as session:
            return self._control_state_from_model(self._get_or_create_control_state(session))

    def update_control_state(self, data: dict[str, object]) -> ControlState:
        with _session_scope() as session:
            control_state = self._get_or_create_control_state(session)

            if "mode" in data and data["mode"] is not None:
                control_state.mode = str(data["mode"])
            if "vj_mode" in data and data["vj_mode"] is not None:
                control_state.vj_mode = parse_vj_mode_string(
                    str(data["vj_mode"])
                ).value
            if "theme_name" in data and data["theme_name"] is not None:
                control_state.theme_name = str(data["theme_name"])
            if "display_mode" in data and data["display_mode"] is not None:
                control_state.display_mode = self._normalize_display_mode(
                    str(data["display_mode"])
                )
            if "manual_fixture_dimmers" in data and data["manual_fixture_dimmers"] is not None:
                incoming = data["manual_fixture_dimmers"]
                if not isinstance(incoming, dict):
                    raise TypeError("manual_fixture_dimmers must be a JSON object")
                merged = dict(control_state.manual_fixture_dimmers or {})
                for k, v in incoming.items():
                    merged[str(k)] = max(0.0, min(1.0, float(v)))
                control_state.manual_fixture_dimmers = merged
            if "show_waveform" in data:
                control_state.show_waveform = bool(data["show_waveform"])
            if "show_fixture_mode" in data:
                control_state.display_mode = (
                    "venue"
                    if bool(data["show_fixture_mode"])
                    else "dmx_heatmap"
                )
            if "active_venue_id" in data:
                active_venue_id = data["active_venue_id"]
                if active_venue_id in (None, ""):
                    control_state.active_venue_id = None
                else:
                    venue = session.get(VenueModel, str(active_venue_id))
                    if venue is None:
                        raise KeyError(f"Venue not found: {active_venue_id}")
                    self._set_active_venue(session, control_state, venue.id)

            # Keep legacy boolean column aligned while callers migrate.
            control_state.show_fixture_mode = control_state.display_mode == "venue"

            self._touch_control_state(control_state)
            return self._control_state_from_model(control_state)

    def get_active_venue_snapshot(self) -> VenueSnapshot | None:
        with _session_scope() as session:
            control_state = self._get_or_create_control_state(session)
            venue = self._resolve_active_venue(session, control_state)
            if venue is None:
                return None
            self._ensure_scene_objects(session, venue)
            self._ensure_lighting_modes(session, venue)
            self._normalize_metric_scene_units(venue)
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def get_venue_snapshot(self, venue_id: str) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            self._ensure_scene_objects(session, venue)
            self._ensure_lighting_modes(session, venue)
            self._normalize_metric_scene_units(venue)
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def list_named_positions(self) -> list[NamedPositionSpec]:
        with _session_scope() as session:
            rows = session.scalars(
                select(NamedPositionModel).order_by(NamedPositionModel.name)
            ).all()
            return [self._named_position_from_model(row) for row in rows]

    def create_named_position(self, name: object) -> NamedPositionSpec:
        normalized_name = _normalize_named_position_name(name)
        with _session_scope() as session:
            existing = session.scalar(
                select(NamedPositionModel).where(
                    NamedPositionModel.name == normalized_name
                )
            )
            if existing is not None:
                raise ValueError(f"Named position already exists: {normalized_name}")
            row = NamedPositionModel(name=normalized_name)
            session.add(row)
            session.flush()
            return self._named_position_from_model(row)

    def update_named_position(
        self, named_position_id: str, data: dict[str, object]
    ) -> NamedPositionSpec:
        with _session_scope() as session:
            row = session.get(NamedPositionModel, named_position_id)
            if row is None:
                raise KeyError(f"Named position not found: {named_position_id}")
            if "name" in data:
                normalized_name = _normalize_named_position_name(data["name"])
                existing = session.scalar(
                    select(NamedPositionModel).where(
                        NamedPositionModel.name == normalized_name,
                        NamedPositionModel.id != named_position_id,
                    )
                )
                if existing is not None:
                    raise ValueError(f"Named position already exists: {normalized_name}")
                row.name = normalized_name
                self._touch_all_venues(session)
            session.flush()
            return self._named_position_from_model(row)

    def delete_named_position(self, named_position_id: str) -> None:
        with _session_scope() as session:
            row = session.get(NamedPositionModel, named_position_id)
            if row is None:
                raise KeyError(f"Named position not found: {named_position_id}")
            session.delete(row)
            self._touch_all_venues(session)

    def create_lighting_mode(
        self,
        venue_id: str,
        data: dict[str, object],
    ) -> VenueSnapshot:
        key = _normalize_lighting_mode_key(data.get("key", data.get("label", "")))
        label = str(data.get("label") or _lighting_mode_label_from_key(key)).strip()
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            self._ensure_lighting_modes(session, venue)
            existing = session.scalar(
                select(LightingModeModel).where(
                    LightingModeModel.venue_id == venue_id,
                    LightingModeModel.key == key,
                )
            )
            if existing is not None:
                raise ValueError(f"Lighting mode already exists: {key}")
            order_index = len(venue.lighting_modes)
            mode = LightingModeModel(
                venue_id=venue_id,
                key=key,
                label=label or _lighting_mode_label_from_key(key),
                order_index=order_index,
                editable=True,
                entry_seconds=_normalize_entry_seconds(
                    data.get("entry_seconds", _lighting_mode_entry_seconds_from_key(key))
                ),
            )
            session.add(mode)
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def update_lighting_mode(
        self,
        venue_id: str,
        lighting_mode_id: str,
        data: dict[str, object],
    ) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            mode = session.get(LightingModeModel, lighting_mode_id)
            if mode is None or mode.venue_id != venue_id:
                raise KeyError(f"Lighting mode not found: {lighting_mode_id}")
            if not mode.editable:
                raise ValueError(f"Lighting mode {mode.key!r} is not editable")
            if "label" in data and data["label"] is not None:
                label = str(data["label"]).strip()
                if not label:
                    raise ValueError("Lighting mode label cannot be empty")
                mode.label = label
            if "order_index" in data and data["order_index"] is not None:
                mode.order_index = int(data["order_index"])
            if "entry_seconds" in data and data["entry_seconds"] is not None:
                mode.entry_seconds = _normalize_entry_seconds(data["entry_seconds"])
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def delete_lighting_mode(self, venue_id: str, lighting_mode_id: str) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            mode = session.get(LightingModeModel, lighting_mode_id)
            if mode is None or mode.venue_id != venue_id:
                raise KeyError(f"Lighting mode not found: {lighting_mode_id}")
            if not mode.editable:
                raise ValueError(f"Lighting mode {mode.key!r} is not editable")
            session.delete(mode)
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def create_animation_assignment(
        self,
        venue_id: str,
        data: dict[str, object],
    ) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            self._ensure_lighting_modes(session, venue)
            lighting_mode = self._resolve_lighting_mode_for_animation(session, venue_id, data)
            spec = data.get("animation_spec")
            if not isinstance(spec, dict):
                raise TypeError("animation_spec must be a JSON object")
            fixture_type = data.get("fixture_type")
            assignment = VenueAnimationAssignmentModel(
                venue_id=venue_id,
                lighting_mode_id=lighting_mode.id,
                fixture_group_name=(
                    str(data["fixture_group_name"]).strip()
                    if data.get("fixture_group_name") not in (None, "")
                    else None
                ),
                fixture_type=(
                    normalize_fixture_type_key(str(fixture_type))
                    if fixture_type not in (None, "")
                    and str(fixture_type) not in ("par", "moving_head")
                    else (str(fixture_type) if fixture_type not in (None, "") else None)
                ),
                order_index=int(data.get("order_index", len(venue.animation_assignments))),
                animation_spec=dict(spec),
            )
            session.add(assignment)
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def update_animation_assignment(
        self,
        venue_id: str,
        assignment_id: str,
        data: dict[str, object],
    ) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            assignment = session.get(VenueAnimationAssignmentModel, assignment_id)
            if assignment is None or assignment.venue_id != venue_id:
                raise KeyError(f"Animation assignment not found: {assignment_id}")
            if "lighting_mode_id" in data or "lighting_mode_key" in data:
                assignment.lighting_mode_id = self._resolve_lighting_mode_for_animation(
                    session, venue_id, data
                ).id
            if "fixture_group_name" in data:
                assignment.fixture_group_name = (
                    str(data["fixture_group_name"]).strip()
                    if data.get("fixture_group_name") not in (None, "")
                    else None
                )
            if "fixture_type" in data:
                raw_type = data.get("fixture_type")
                assignment.fixture_type = (
                    normalize_fixture_type_key(str(raw_type))
                    if raw_type not in (None, "")
                    and str(raw_type) not in ("par", "moving_head")
                    else (str(raw_type) if raw_type not in (None, "") else None)
                )
            if "order_index" in data and data["order_index"] is not None:
                assignment.order_index = int(data["order_index"])
            if "animation_spec" in data:
                if not isinstance(data["animation_spec"], dict):
                    raise TypeError("animation_spec must be a JSON object")
                assignment.animation_spec = dict(data["animation_spec"])
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def delete_animation_assignment(
        self,
        venue_id: str,
        assignment_id: str,
    ) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            assignment = session.get(VenueAnimationAssignmentModel, assignment_id)
            if assignment is None or assignment.venue_id != venue_id:
                raise KeyError(f"Animation assignment not found: {assignment_id}")
            session.delete(assignment)
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def upsert_fixture_named_position(
        self,
        venue_id: str,
        fixture_id: str,
        named_position_id: str,
        data: dict[str, object],
    ) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            fixture = session.get(FixtureModel, fixture_id)
            if fixture is None or fixture.venue_id != venue_id:
                raise KeyError(f"Fixture not found: {fixture_id}")
            named_position = session.get(NamedPositionModel, named_position_id)
            if named_position is None:
                raise KeyError(f"Named position not found: {named_position_id}")

            row = session.scalar(
                select(FixtureNamedPositionModel).where(
                    FixtureNamedPositionModel.fixture_id == fixture_id,
                    FixtureNamedPositionModel.named_position_id == named_position_id,
                )
            )
            if row is None:
                row = FixtureNamedPositionModel(
                    venue_id=venue_id,
                    fixture_id=fixture_id,
                    named_position_id=named_position_id,
                    pan=0.0,
                    tilt=0.0,
                )
                session.add(row)
            row.pan = _clamp_dmx_float(data.get("pan", row.pan))
            row.tilt = _clamp_dmx_float(data.get("tilt", row.tilt))
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def delete_fixture_named_position(
        self,
        venue_id: str,
        fixture_id: str,
        named_position_id: str,
    ) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            fixture = session.get(FixtureModel, fixture_id)
            if fixture is None or fixture.venue_id != venue_id:
                raise KeyError(f"Fixture not found: {fixture_id}")
            row = session.scalar(
                select(FixtureNamedPositionModel).where(
                    FixtureNamedPositionModel.fixture_id == fixture_id,
                    FixtureNamedPositionModel.named_position_id == named_position_id,
                )
            )
            if row is None:
                raise KeyError(
                    f"Fixture named position not found: {fixture_id}/{named_position_id}"
                )
            session.delete(row)
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def set_active_venue(self, venue_id: str) -> VenueSnapshot:
        with _session_scope() as session:
            control_state = self._get_or_create_control_state(session)
            venues = session.scalars(select(VenueModel)).all()
            target = None
            for venue in venues:
                if venue.id == venue_id:
                    target = venue
                    break
            if target is None:
                raise KeyError(f"Venue not found: {venue_id}")
            self._ensure_lighting_modes(session, target)
            self._set_active_venue(session, control_state, target.id)
            return self._snapshot_from_model(target)

    def create_venue(self, name: str) -> VenueSnapshot:
        with _session_scope() as session:
            slug = self._next_available_slug(session, _slugify(name))
            venue = VenueModel(
                slug=slug,
                name=name,
                active=False,
                archived=False,
                revision=1,
            )
            session.add(venue)
            session.flush()
            self._ensure_scene_objects(session, venue)
            self._ensure_lighting_modes(session, venue)
            self._sync_legacy_scene_fields(venue)
            return self._snapshot_from_model(venue)

    def update_venue(self, venue_id: str, data: dict[str, object]) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            self._ensure_scene_objects(session, venue)
            self._ensure_lighting_modes(session, venue)
            floor_object = self._scene_object_by_kind(venue, "floor")

            if "name" in data and data["name"] is not None:
                venue.name = str(data["name"])
                if "slug" not in data:
                    venue.slug = self._next_available_slug(
                        session, _slugify(venue.name), current_venue_id=venue.id
                    )
            if "slug" in data and data["slug"]:
                venue.slug = self._next_available_slug(
                    session, _slugify(str(data["slug"])), current_venue_id=venue.id
                )
            if "archived" in data:
                venue.archived = bool(data["archived"])
            if "floor_width" in data:
                floor_object.width = float(data["floor_width"])
                floor_object.x = 0.0
            if "floor_depth" in data:
                floor_object.height = float(data["floor_depth"])
                floor_object.y = 0.0
            if "floor_height" in data:
                floor_object.options = {
                    **dict(floor_object.options or {}),
                    "room_height": float(data["floor_height"]),
                }
            if "manual_dimmer_supported" in data:
                venue.manual_dimmer_supported = bool(data["manual_dimmer_supported"])
            if "active" in data and bool(data["active"]):
                control_state = self._get_or_create_control_state(session)
                self._set_active_venue(session, control_state, venue.id)
            self._sync_legacy_scene_fields(venue)
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def update_video_wall(self, venue_id: str, data: dict[str, object]) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            self._ensure_scene_objects(session, venue)
            video_wall = self._scene_object_by_kind(venue, "video_wall")

            if "video_wall_x" in data and data["video_wall_x"] is not None:
                video_wall.x = float(data["video_wall_x"])
            if "video_wall_y" in data and data["video_wall_y"] is not None:
                video_wall.y = float(data["video_wall_y"])
            if "video_wall_z" in data and data["video_wall_z"] is not None:
                video_wall.z = float(data["video_wall_z"])
            if "video_wall_width" in data and data["video_wall_width"] is not None:
                video_wall.width = float(data["video_wall_width"])
            if "video_wall_height" in data and data["video_wall_height"] is not None:
                video_wall.height = float(data["video_wall_height"])
            if "video_wall_depth" in data and data["video_wall_depth"] is not None:
                video_wall.depth = float(data["video_wall_depth"])
            if "video_wall_locked" in data:
                video_wall.locked = bool(data["video_wall_locked"])

            self._sync_legacy_scene_fields(venue)
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def update_scene_object(
        self, venue_id: str, scene_object_kind: str, data: dict[str, object]
    ) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            self._ensure_scene_objects(session, venue)
            scene_object = self._scene_object_by_kind(venue, scene_object_kind)

            for key in ("x", "y", "z", "width", "height", "depth"):
                if key in data and data[key] is not None:
                    setattr(scene_object, key, float(data[key]))
            for key in ("rotation_x", "rotation_y", "rotation_z"):
                if key in data and data[key] is not None:
                    setattr(scene_object, key, float(data[key]))
            if "locked" in data:
                scene_object.locked = bool(data["locked"])
            if "options" in data and data["options"] is not None:
                scene_object.options = dict(data["options"])

            self._sync_legacy_scene_fields(venue)
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def add_fixture(self, venue_id: str, fixture_data: dict[str, object]) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")

            next_order = len(venue.fixtures)
            fixture_type_str = normalize_fixture_type_key(str(fixture_data["fixture_type"]))
            if _is_manual_dimmer_channel_type(fixture_type_str):
                is_manual = True
            else:
                is_manual = bool(fixture_data.get("is_manual", False))

            # Seed per-type defaults (e.g. pan/tilt range for moving heads) into
            # `options` so a freshly-created fixture exposes them as editable fields.
            # Client-supplied options and top-level range fields win over defaults.
            seeded_options: dict[str, object] = {}
            if fixture_type_has_pan_tilt_range(fixture_type_str):
                seeded_options.update(pan_tilt_range_default_options(fixture_type_str))
            if "options" in fixture_data:
                seeded_options.update(dict(fixture_data["options"]))  # type: ignore[arg-type]
            seeded_options.update(_extract_pan_tilt_range(fixture_data))

            fixture = FixtureModel(
                id=str(fixture_data.get("id", uuid.uuid4())),
                venue_id=venue_id,
                order_index=next_order,
                fixture_type=fixture_type_str,
                name=(
                    None
                    if fixture_data.get("name") in (None, "")
                    else str(fixture_data["name"])
                ),
                group_name=(
                    None
                    if fixture_data.get("group_name") in (None, "")
                    else str(fixture_data["group_name"])
                ),
                is_manual=is_manual,
                address=int(fixture_data["address"]),
                universe=_normalize_universe(fixture_data.get("universe", "default")),
                x=float(fixture_data.get("x", 0.0)),
                y=float(fixture_data.get("y", 0.0)),
                z=float(fixture_data.get("z", 0.0)),
                rotation_x=float(fixture_data.get("rotation_x", 0.0)),
                rotation_y=float(fixture_data.get("rotation_y", 0.0)),
                rotation_z=float(fixture_data.get("rotation_z", 0.0)),
                options=seeded_options,
            )
            session.add(fixture)
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def update_fixture(
        self, venue_id: str, fixture_id: str, fixture_data: dict[str, object]
    ) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            fixture = session.get(FixtureModel, fixture_id)
            if fixture is None or fixture.venue_id != venue_id:
                raise KeyError(f"Fixture not found: {fixture_id}")

            old_fixture_type = fixture.fixture_type

            for key in (
                "fixture_type",
                "name",
                "group_name",
                "universe",
            ):
                if key in fixture_data:
                    value = fixture_data[key]
                    if key == "universe":
                        setattr(fixture, key, _normalize_universe(value))
                    elif key == "fixture_type":
                        setattr(
                            fixture,
                            key,
                            None if value in (None, "") else normalize_fixture_type_key(str(value)),
                        )
                    elif key == "name":
                        if value in (None, ""):
                            fixture.name = None
                        else:
                            fixture.name = str(value).strip() or None
                    else:
                        setattr(
                            fixture,
                            key,
                            None if value in (None, "") and key != "fixture_type" else value,
                        )

            for key in ("is_manual",):
                if key in fixture_data:
                    setattr(fixture, key, bool(fixture_data[key]))

            for key in ("address",):
                if key in fixture_data:
                    setattr(fixture, key, int(fixture_data[key]))

            for key in ("x", "y", "z", "rotation_x", "rotation_y", "rotation_z"):
                if key in fixture_data:
                    setattr(fixture, key, float(fixture_data[key]))

            range_overrides = _extract_pan_tilt_range(fixture_data)
            if "options" in fixture_data or range_overrides:
                fixture.options = _merge_pan_tilt_range_into_options(
                    existing_options=dict(fixture.options or {}),
                    explicit_options=(
                        dict(fixture_data["options"])  # type: ignore[arg-type]
                        if "options" in fixture_data
                        else None
                    ),
                    range_overrides=range_overrides,
                )

            if _is_manual_dimmer_channel_type(fixture.fixture_type):
                fixture.is_manual = True
            elif (
                _is_manual_dimmer_channel_type(old_fixture_type)
                and not _is_manual_dimmer_channel_type(fixture.fixture_type)
                and "is_manual" not in fixture_data
            ):
                fixture.is_manual = False

            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def delete_fixture(self, venue_id: str, fixture_id: str) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            fixture = session.get(FixtureModel, fixture_id)
            if fixture is None or fixture.venue_id != venue_id:
                raise KeyError(f"Fixture not found: {fixture_id}")
            session.delete(fixture)
            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    @beartype
    def magic_repatch_fixtures_compact(self, venue_id: str) -> VenueSnapshot:
        """Assign DMX addresses per universe starting at 1 with no gaps (fixed order)."""
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")

            by_universe: dict[str, list[FixtureModel]] = defaultdict(list)
            for fx in venue.fixtures:
                by_universe[str(fx.universe)].append(fx)

            for universe, fixtures in by_universe.items():
                fixtures.sort(key=lambda f: (f.order_index, f.id))
                next_addr = 1
                for fx in fixtures:
                    w = dmx_address_width_for_fixture(
                        str(fx.fixture_type),
                        dict(fx.options or {}),
                    )
                    if next_addr + w - 1 > 512:
                        raise ValueError(
                            f"Universe {universe!r}: need more than 512 channels "
                            f"(next slot {next_addr}, footprint {w}). "
                            "Move some fixtures to another universe first."
                        )
                    fx.address = next_addr
                    next_addr += w

            self._touch_venue(venue)
            session.flush()
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def ensure_seed_data(self) -> RuntimeBootstrap:
        for seed in build_seed_venues():
            self._upsert_seed(seed)
        self._ensure_all_venues_have_lighting_modes()
        return self.get_runtime_bootstrap()

    def _ensure_all_venues_have_lighting_modes(self) -> None:
        with _session_scope() as session:
            for venue in session.scalars(select(VenueModel)).all():
                self._ensure_lighting_modes(session, venue)

    def _upsert_seed(self, seed: SeedVenueDefinition) -> None:
        with _session_scope() as session:
            venue = session.scalar(select(VenueModel).where(VenueModel.slug == seed.slug))
            if venue is None:
                venue = VenueModel(
                    slug=seed.slug,
                    name=seed.name,
                    active=seed.active,
                )
                session.add(venue)
                session.flush()

            venue.name = seed.name
            venue.archived = seed.archived
            venue.floor_width = seed.floor_width
            venue.floor_depth = seed.floor_depth
            venue.floor_height = seed.floor_height
            venue.video_wall_x = seed.video_wall.x
            venue.video_wall_y = seed.video_wall.y
            venue.video_wall_z = seed.video_wall.z
            venue.video_wall_width = seed.video_wall.width
            venue.video_wall_height = seed.video_wall.height
            venue.video_wall_depth = seed.video_wall.depth
            venue.video_wall_locked = seed.video_wall.locked
            venue.manual_dimmer_supported = seed.manual_dimmer_supported
            self._upsert_scene_objects(venue, seed.scene_objects)

            existing_by_id = {fixture.id: fixture for fixture in venue.fixtures}
            seed_ids = {fixture.id for fixture in seed.fixtures}

            for fixture in list(venue.fixtures):
                if fixture.id not in seed_ids:
                    session.delete(fixture)

            for order_index, fixture_spec in enumerate(seed.fixtures):
                fixture_model = existing_by_id.get(fixture_spec.id)
                if fixture_model is None:
                    fixture_model = FixtureModel(id=fixture_spec.id, venue_id=venue.id)
                    session.add(fixture_model)
                fixture_model.order_index = order_index
                fixture_model.fixture_type = fixture_spec.fixture_type
                fixture_model.name = fixture_spec.name
                fixture_model.group_name = fixture_spec.group_name
                fixture_model.is_manual = fixture_spec.is_manual
                fixture_model.address = fixture_spec.address
                fixture_model.universe = fixture_spec.universe
                fixture_model.x = fixture_spec.x
                fixture_model.y = fixture_spec.y
                fixture_model.z = fixture_spec.z
                fixture_model.rotation_x = fixture_spec.rotation_x
                fixture_model.rotation_y = fixture_spec.rotation_y
                fixture_model.rotation_z = fixture_spec.rotation_z
                fixture_model.options = dict(fixture_spec.options)

            self._ensure_lighting_modes(session, venue)
            self._touch_venue(venue)

    def _resolve_lighting_mode_for_animation(
        self,
        session,
        venue_id: str,
        data: dict[str, object],
    ) -> LightingModeModel:
        lighting_mode_id = data.get("lighting_mode_id")
        if lighting_mode_id not in (None, ""):
            mode = session.get(LightingModeModel, str(lighting_mode_id))
            if mode is None or mode.venue_id != venue_id:
                raise KeyError(f"Lighting mode not found: {lighting_mode_id}")
            return mode
        if data.get("lighting_mode_key") not in (None, ""):
            key = _normalize_lighting_mode_key(data["lighting_mode_key"])
        elif data.get("mode_key") not in (None, ""):
            key = _normalize_lighting_mode_key(data["mode_key"])
        else:
            raise ValueError("lighting_mode_id or lighting_mode_key is required")
        mode = session.scalar(
            select(LightingModeModel).where(
                LightingModeModel.venue_id == venue_id,
                LightingModeModel.key == key,
            )
        )
        if mode is None:
            raise KeyError(f"Lighting mode not found: {key}")
        return mode

    def _ensure_lighting_modes(self, session, venue: VenueModel) -> None:
        if venue.lighting_modes:
            removed_mode_keys = self._remove_legacy_default_mode_assignments(session, venue)
            self._seed_default_animation_assignments(
                session,
                venue,
                {mode.key: mode for mode in venue.lighting_modes},
                only_mode_keys=removed_mode_keys,
            )
            return

        modes = list(DEFAULT_EDITABLE_LIGHTING_MODES)
        is_queer_prom = (
            "queer-prom" in venue.slug.casefold()
            or "queer prom" in venue.name.casefold()
        )
        if is_queer_prom:
            modes.append(("ethereal", "Ethereal"))

        created: dict[str, LightingModeModel] = {}
        for order_index, (key, label) in enumerate(modes):
            row = LightingModeModel(
                venue_id=venue.id,
                key=key,
                label=label,
                order_index=order_index,
                editable=True,
                entry_seconds=_lighting_mode_entry_seconds_from_key(key),
            )
            session.add(row)
            created[key] = row
        session.flush()

        self._seed_default_animation_assignments(session, venue, created)

    def _remove_legacy_default_mode_assignments(
        self,
        session,
        venue: VenueModel,
    ) -> set[str]:
        removed_mode_keys: set[str] = set()
        for assignment in list(venue.animation_assignments):
            if assignment.animation_spec.get("type") != "legacy_mode":
                continue
            if assignment.animation_spec.get("mode") != assignment.lighting_mode.key:
                continue
            removed_mode_keys.add(assignment.lighting_mode.key)
            session.delete(assignment)
        if removed_mode_keys:
            session.flush()
            self._touch_venue(venue)
        return removed_mode_keys

    def _seed_default_animation_assignments(
        self,
        session,
        venue: VenueModel,
        modes_by_key: dict[str, LightingModeModel],
        *,
        only_mode_keys: set[str] | None = None,
    ) -> None:
        mode_keys = set(DEFAULT_LIGHTING_MODE_ANIMATION_ROWS)
        if only_mode_keys is not None:
            mode_keys &= only_mode_keys

        for mode_key in mode_keys:
            mode = modes_by_key.get(mode_key)
            if mode is None:
                continue
            if any(
                assignment.lighting_mode_id == mode.id
                and assignment not in session.deleted
                for assignment in venue.animation_assignments
            ):
                continue
            rows = DEFAULT_LIGHTING_MODE_ANIMATION_ROWS[mode_key]
            for order_index, (fixture_type, animation_spec) in enumerate(rows):
                session.add(
                    VenueAnimationAssignmentModel(
                        venue_id=venue.id,
                        lighting_mode_id=mode.id,
                        fixture_group_name=None,
                        fixture_type=fixture_type,
                        order_index=order_index,
                        animation_spec=dict(animation_spec),
                    )
                )

    def _touch_venue(self, venue: VenueModel) -> None:
        venue.revision = int(venue.revision) + 1
        venue.updated_at = datetime.utcnow()

    def _touch_all_venues(self, session) -> None:
        for venue in session.scalars(select(VenueModel)).all():
            self._touch_venue(venue)

    def _touch_control_state(self, control_state: ControlStateModel) -> None:
        control_state.updated_at = datetime.utcnow()

    def _summary_from_model(self, venue: VenueModel) -> VenueSummary:
        return VenueSummary(
            id=venue.id,
            slug=venue.slug,
            name=venue.name,
            archived=venue.archived,
            active=venue.active,
            revision=venue.revision,
        )

    def _all_named_position_models(self, venue: VenueModel) -> list[NamedPositionModel]:
        session = object_session(venue)
        if session is None:
            return []
        return list(
            session.scalars(
                select(NamedPositionModel).order_by(NamedPositionModel.name)
            ).all()
        )

    def _named_position_from_model(
        self, position: NamedPositionModel
    ) -> NamedPositionSpec:
        return NamedPositionSpec(
            id=position.id,
            name=position.name,
        )

    def _fixture_named_position_from_model(
        self, position: FixtureNamedPositionModel
    ) -> FixtureNamedPositionSpec:
        named_position = position.named_position
        return FixtureNamedPositionSpec(
            id=position.id,
            venue_id=position.venue_id,
            fixture_id=position.fixture_id,
            named_position_id=position.named_position_id,
            position_name="" if named_position is None else named_position.name,
            pan=position.pan,
            tilt=position.tilt,
        )

    def _lighting_mode_from_model(self, mode: LightingModeModel) -> LightingModeSpec:
        return LightingModeSpec(
            id=mode.id,
            venue_id=mode.venue_id,
            key=mode.key,
            label=mode.label,
            order_index=mode.order_index,
            editable=mode.editable,
            entry_seconds=mode.entry_seconds,
        )

    def _animation_assignment_from_model(
        self, assignment: VenueAnimationAssignmentModel
    ) -> VenueAnimationAssignmentSpec:
        lighting_mode = assignment.lighting_mode
        return VenueAnimationAssignmentSpec(
            id=assignment.id,
            venue_id=assignment.venue_id,
            lighting_mode_id=assignment.lighting_mode_id,
            lighting_mode_key="" if lighting_mode is None else lighting_mode.key,
            fixture_group_name=assignment.fixture_group_name,
            fixture_type=assignment.fixture_type,
            order_index=assignment.order_index,
            animation_spec=dict(assignment.animation_spec or {}),
        )

    def _snapshot_from_model(self, venue: VenueModel) -> VenueSnapshot:
        scene_objects = tuple(
            self._scene_object_from_model(scene_object)
            for scene_object in sorted(venue.scene_objects, key=lambda item: item.order_index)
        )
        floor_object = next(
            (scene_object for scene_object in scene_objects if scene_object.kind == "floor"),
            None,
        )
        video_wall_object = next(
            (scene_object for scene_object in scene_objects if scene_object.kind == "video_wall"),
            None,
        )
        fixtures = tuple(
            FixtureSpec(
                id=fixture.id,
                fixture_type=normalize_fixture_type_key(fixture.fixture_type),
                address=fixture.address,
                universe=fixture.universe,
                x=fixture.x,
                y=fixture.y,
                z=fixture.z,
                rotation_x=fixture.rotation_x,
                rotation_y=fixture.rotation_y,
                rotation_z=fixture.rotation_z,
                name=fixture.name,
                group_name=fixture.group_name,
                is_manual=fixture.is_manual,
                options=_hydrate_pan_tilt_range(
                    fixture.fixture_type, dict(fixture.options or {})
                ),
            )
            for fixture in venue.fixtures
        )
        named_positions = tuple(
            self._named_position_from_model(position)
            for position in self._all_named_position_models(venue)
        )
        fixture_named_positions = tuple(
            self._fixture_named_position_from_model(position)
            for position in sorted(
                venue.fixture_named_positions,
                key=lambda item: (
                    item.fixture.order_index if item.fixture is not None else 0,
                    item.named_position.name if item.named_position is not None else "",
                ),
            )
        )
        lighting_modes = tuple(
            self._lighting_mode_from_model(mode)
            for mode in sorted(venue.lighting_modes, key=lambda item: item.order_index)
        )
        animation_assignments = tuple(
            self._animation_assignment_from_model(assignment)
            for assignment in sorted(
                venue.animation_assignments,
                key=lambda item: (
                    item.lighting_mode.order_index if item.lighting_mode is not None else 0,
                    item.fixture_group_name or "",
                    item.fixture_type or "",
                    item.order_index,
                ),
            )
        )
        return VenueSnapshot(
            summary=self._summary_from_model(venue),
            floor_width=(
                floor_object.width if floor_object is not None else venue.floor_width
            ),
            floor_depth=(
                floor_object.height if floor_object is not None else venue.floor_depth
            ),
            floor_height=(
                float(floor_object.options.get("room_height", venue.floor_height))
                if floor_object is not None
                else venue.floor_height
            ),
            video_wall=VideoWallSpec(
                x=video_wall_object.x if video_wall_object is not None else venue.video_wall_x,
                y=video_wall_object.y if video_wall_object is not None else venue.video_wall_y,
                z=video_wall_object.z if video_wall_object is not None else venue.video_wall_z,
                width=(
                    video_wall_object.width
                    if video_wall_object is not None
                    else venue.video_wall_width
                ),
                height=(
                    video_wall_object.height
                    if video_wall_object is not None
                    else venue.video_wall_height
                ),
                depth=(
                    video_wall_object.depth
                    if video_wall_object is not None
                    else venue.video_wall_depth
                ),
                locked=(
                    video_wall_object.locked
                    if video_wall_object is not None
                    else venue.video_wall_locked
                ),
            ),
            fixtures=fixtures,
            scene_objects=scene_objects,
            named_positions=named_positions,
            fixture_named_positions=fixture_named_positions,
            lighting_modes=lighting_modes,
            animation_assignments=animation_assignments,
        )

    def _control_state_from_model(self, control_state: ControlStateModel) -> ControlState:
        raw_mfd = getattr(control_state, "manual_fixture_dimmers", None) or {}
        manual_fixture_dimmers: dict[str, float] = {}
        if isinstance(raw_mfd, dict):
            for k, v in raw_mfd.items():
                try:
                    manual_fixture_dimmers[str(k)] = max(0.0, min(1.0, float(v)))
                except (TypeError, ValueError):
                    continue
        return ControlState(
            mode=control_state.mode,
            vj_mode=parse_vj_mode_string(control_state.vj_mode).value,
            theme_name=control_state.theme_name,
            active_venue_id=control_state.active_venue_id,
            display_mode=self._normalize_display_mode(control_state.display_mode),
            show_waveform=control_state.show_waveform,
            manual_fixture_dimmers=manual_fixture_dimmers,
        )

    def _get_or_create_control_state(self, session) -> ControlStateModel:
        control_state = session.get(ControlStateModel, 1)
        if control_state is not None:
            return control_state

        active_venue = session.scalar(
            select(VenueModel).where(VenueModel.active.is_(True)).limit(1)
        )
        control_state = ControlStateModel(
            id=1,
            mode="chill",
            vj_mode="prom_dmack",
            theme_name="Rave",
            active_venue_id=active_venue.id if active_venue is not None else None,
            display_mode="dmx_heatmap",
            manual_fixture_dimmers={},
            hype_limiter=False,
            show_waveform=True,
            show_fixture_mode=False,
        )
        session.add(control_state)
        session.flush()
        return control_state

    def _normalize_display_mode(self, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized in DISPLAY_MODE_VALUES:
            return normalized
        if normalized == "fixture_scene":
            return "venue"
        return "dmx_heatmap"

    def _resolve_active_venue(
        self, session, control_state: ControlStateModel
    ) -> VenueModel | None:
        venue: VenueModel | None = None
        if control_state.active_venue_id:
            venue = session.get(VenueModel, control_state.active_venue_id)
        if venue is None:
            venue = session.scalar(select(VenueModel).where(VenueModel.active.is_(True)))
        if venue is None:
            venue = session.scalar(select(VenueModel).order_by(VenueModel.name).limit(1))
        if venue is not None and control_state.active_venue_id != venue.id:
            self._set_active_venue(session, control_state, venue.id)
        return venue

    def _set_active_venue(
        self, session, control_state: ControlStateModel, venue_id: str
    ) -> None:
        control_state.active_venue_id = venue_id
        self._touch_control_state(control_state)
        venues = session.scalars(select(VenueModel)).all()
        for venue in venues:
            is_target = venue.id == venue_id
            if venue.active != is_target:
                venue.active = is_target
                self._touch_venue(venue)

    def _next_available_slug(
        self, session, base_slug: str, current_venue_id: str | None = None
    ) -> str:
        slug = base_slug
        suffix = 2
        while True:
            existing = session.scalar(select(VenueModel).where(VenueModel.slug == slug))
            if existing is None or existing.id == current_venue_id:
                return slug
            slug = f"{base_slug}-{suffix}"
            suffix += 1

    def _ensure_scene_objects(self, session, venue: VenueModel) -> None:
        existing_by_kind = {scene_object.kind: scene_object for scene_object in venue.scene_objects}
        defaults = self._default_scene_objects(venue)
        for order_index, scene_object_spec in enumerate(defaults):
            scene_object = existing_by_kind.get(scene_object_spec.kind)
            created = False
            if scene_object is None:
                scene_object = SceneObjectModel(id=scene_object_spec.id, venue_id=venue.id)
                session.add(scene_object)
                venue.scene_objects.append(scene_object)
                created = True
            if not scene_object.kind:
                scene_object.kind = scene_object_spec.kind
            # Only apply default geometry when inserting a new row. Existing objects (e.g. dj_table
            # with empty options) must not be overwritten on unrelated updates (video wall, etc.).
            if created:
                self._apply_scene_object_spec(scene_object, scene_object_spec, order_index)
            scene_object.order_index = order_index
        self._normalize_metric_scene_units(venue)
        self._sync_legacy_scene_fields(venue)

    def _default_scene_objects(self, venue: VenueModel) -> tuple[SceneObjectSpec, ...]:
        floor_width = max(float(venue.floor_width or 20.0), 1.0)
        floor_depth = max(float(venue.floor_depth or 15.0), 1.0)
        room_height = float(venue.floor_height or 10.0)
        table_width = DJ_TABLE_WIDTH_METERS
        table_depth = DJ_TABLE_DEPTH_METERS
        table_height = DJ_TABLE_HEIGHT_METERS
        table_y = -(floor_depth / 2.0) + 1.2
        return (
            SceneObjectSpec(
                id=f"{venue.id}:floor",
                kind="floor",
                x=0.0,
                y=0.0,
                z=-0.04,
                width=floor_width,
                height=floor_depth,
                depth=0.08,
                options={"room_height": room_height},
            ),
            SceneObjectSpec(
                id=f"{venue.id}:video_wall",
                kind="video_wall",
                x=float(venue.video_wall_x or 0.0),
                y=float(venue.video_wall_y or (-(floor_depth / 2.0) + 0.4)),
                z=float(venue.video_wall_z or 3.0),
                width=float(venue.video_wall_width or floor_width),
                height=float(venue.video_wall_height or 6.0),
                depth=float(venue.video_wall_depth or max(floor_depth * 0.025, 0.2)),
                locked=bool(venue.video_wall_locked),
            ),
            SceneObjectSpec(
                id=f"{venue.id}:dj_table",
                kind="dj_table",
                x=0.0,
                y=table_y,
                z=table_height / 2.0,
                width=table_width,
                height=table_height,
                depth=table_depth,
            ),
            SceneObjectSpec(
                id=f"{venue.id}:dj_cutout",
                kind="dj_cutout",
                x=0.0,
                y=table_y - table_depth / 2.0 - DJ_SILHOUETTE_BEHIND_TABLE_EXTRA_M,
                z=table_height
                + DJ_HEIGHT_METERS / 2.0
                - DJ_SILHOUETTE_CLEARANCE_BELOW_TABLE_TOP_M,
                width=0.9,
                height=DJ_HEIGHT_METERS,
                depth=0.05,
                options={"use_billboard": True},
            ),
        )

    def _upsert_scene_objects(
        self, venue: VenueModel, scene_objects: tuple[SceneObjectSpec, ...]
    ) -> None:
        existing_by_id = {scene_object.id: scene_object for scene_object in venue.scene_objects}
        seed_ids = {scene_object.id for scene_object in scene_objects}
        for scene_object in list(venue.scene_objects):
            if scene_object.id not in seed_ids:
                venue.scene_objects.remove(scene_object)
        for order_index, scene_object_spec in enumerate(scene_objects):
            scene_object_model = existing_by_id.get(scene_object_spec.id)
            if scene_object_model is None:
                scene_object_model = SceneObjectModel(
                    id=scene_object_spec.id,
                    venue_id=venue.id,
                )
                venue.scene_objects.append(scene_object_model)
            self._apply_scene_object_spec(scene_object_model, scene_object_spec, order_index)
        self._sync_legacy_scene_fields(venue)

    def _apply_scene_object_spec(
        self,
        scene_object_model: SceneObjectModel,
        scene_object_spec: SceneObjectSpec,
        order_index: int,
    ) -> None:
        scene_object_model.order_index = order_index
        scene_object_model.kind = scene_object_spec.kind
        scene_object_model.x = scene_object_spec.x
        scene_object_model.y = scene_object_spec.y
        scene_object_model.z = scene_object_spec.z
        scene_object_model.width = scene_object_spec.width
        scene_object_model.height = scene_object_spec.height
        scene_object_model.depth = scene_object_spec.depth
        scene_object_model.rotation_x = scene_object_spec.rotation_x
        scene_object_model.rotation_y = scene_object_spec.rotation_y
        scene_object_model.rotation_z = scene_object_spec.rotation_z
        scene_object_model.locked = scene_object_spec.locked
        scene_object_model.options = dict(scene_object_spec.options)

    def _scene_object_by_kind(self, venue: VenueModel, kind: str) -> SceneObjectModel:
        for scene_object in venue.scene_objects:
            if scene_object.kind == kind:
                return scene_object
        raise KeyError(f"Scene object not found: {kind}")

    def _scene_object_from_model(self, scene_object: SceneObjectModel) -> SceneObjectSpec:
        return SceneObjectSpec(
            id=scene_object.id,
            kind=scene_object.kind,
            x=scene_object.x,
            y=scene_object.y,
            z=scene_object.z,
            width=scene_object.width,
            height=scene_object.height,
            depth=scene_object.depth,
            rotation_x=scene_object.rotation_x,
            rotation_y=scene_object.rotation_y,
            rotation_z=scene_object.rotation_z,
            locked=scene_object.locked,
            options=dict(scene_object.options or {}),
        )

    def _sync_legacy_scene_fields(self, venue: VenueModel) -> None:
        floor_object = next(
            (scene_object for scene_object in venue.scene_objects if scene_object.kind == "floor"),
            None,
        )
        if floor_object is not None:
            venue.floor_width = float(floor_object.width)
            venue.floor_depth = float(floor_object.height)
            venue.floor_height = float(
                dict(floor_object.options or {}).get("room_height", venue.floor_height)
            )

        video_wall = next(
            (
                scene_object
                for scene_object in venue.scene_objects
                if scene_object.kind == "video_wall"
            ),
            None,
        )
        if video_wall is not None:
            venue.video_wall_x = float(video_wall.x)
            venue.video_wall_y = float(video_wall.y)
            venue.video_wall_z = float(video_wall.z)
            venue.video_wall_width = float(video_wall.width)
            venue.video_wall_height = float(video_wall.height)
            venue.video_wall_depth = float(video_wall.depth)
            venue.video_wall_locked = bool(video_wall.locked)

    def _normalize_metric_scene_units(self, venue: VenueModel) -> None:
        floor_object = next(
            (scene_object for scene_object in venue.scene_objects if scene_object.kind == "floor"),
            None,
        )
        if floor_object is None or float(floor_object.width) <= 100.0:
            return

        legacy_floor_width = float(floor_object.width)
        legacy_floor_depth = float(floor_object.height)

        def convert_lateral(value: float) -> float:
            return (value - (legacy_floor_width / 2.0)) / LEGACY_PLAN_UNITS_PER_METER

        def convert_depth(value: float) -> float:
            return (value - (legacy_floor_depth / 2.0)) / LEGACY_PLAN_UNITS_PER_METER

        floor_object.width = legacy_floor_width / LEGACY_PLAN_UNITS_PER_METER
        floor_object.height = legacy_floor_depth / LEGACY_PLAN_UNITS_PER_METER
        floor_object.x = 0.0
        floor_object.y = 0.0

        for scene_object in venue.scene_objects:
            if scene_object.kind == "floor":
                continue
            scene_object.x = convert_lateral(float(scene_object.x))
            scene_object.y = convert_depth(float(scene_object.y))
            scene_object.width = float(scene_object.width) / LEGACY_PLAN_UNITS_PER_METER
            scene_object.depth = float(scene_object.depth) / LEGACY_PLAN_UNITS_PER_METER

        for fixture in venue.fixtures:
            fixture.x = convert_lateral(float(fixture.x))
            fixture.y = convert_depth(float(fixture.y))
