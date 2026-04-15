from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
import uuid

from beartype import beartype
from sqlalchemy import select

from parrot_cloud.domain import (
    ControlState,
    FixtureSpec,
    RuntimeBootstrap,
    SceneObjectSpec,
    VenueSnapshot,
    VenueSummary,
    VideoWallSpec,
)
from parrot_cloud.models import (
    ControlStateModel,
    FixtureModel,
    SceneObjectModel,
    VenueModel,
)
from parrot_cloud.database import create_session, get_repo_root
from parrot_cloud.seeds import SeedVenueDefinition, build_seed_venues
from parrot.utils.dmx_utils import Universe

LEGACY_PLAN_UNITS_PER_METER = 50.0
DJ_HEIGHT_METERS = 1.8288
DJ_TABLE_HEIGHT_METERS = 1.0668
DJ_TABLE_DEPTH_METERS = 1.2192
DJ_TABLE_WIDTH_METERS = 2.4384
# Upstage of the table back edge (venue −y), ~2 ft — silhouette is derived from table + this gap.
DJ_SILHOUETTE_BEHIND_TABLE_EXTRA_M = 0.61


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
    def list_venue_summaries(self) -> list[VenueSummary]:
        with _session_scope() as session:
            venues = session.scalars(select(VenueModel).order_by(VenueModel.name)).all()
            return [self._summary_from_model(venue) for venue in venues]

    def get_runtime_bootstrap(self) -> RuntimeBootstrap:
        venues = tuple(self.list_venue_summaries())
        active_venue = self.get_active_venue_snapshot()
        control_state = self.get_control_state()
        return RuntimeBootstrap(
            venues=venues,
            active_venue=active_venue,
            control_state=control_state,
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
                control_state.vj_mode = str(data["vj_mode"])
            if "theme_name" in data and data["theme_name"] is not None:
                control_state.theme_name = str(data["theme_name"])
            if "manual_dimmer" in data and data["manual_dimmer"] is not None:
                control_state.manual_dimmer = max(
                    0.0, min(1.0, float(data["manual_dimmer"]))
                )
            if "hype_limiter" in data:
                control_state.hype_limiter = bool(data["hype_limiter"])
            if "show_waveform" in data:
                control_state.show_waveform = bool(data["show_waveform"])
            if "show_fixture_mode" in data:
                control_state.show_fixture_mode = bool(data["show_fixture_mode"])

            self._touch_control_state(control_state)
            return self._control_state_from_model(control_state)

    def get_active_venue_snapshot(self) -> VenueSnapshot | None:
        with _session_scope() as session:
            venue = session.scalar(select(VenueModel).where(VenueModel.active.is_(True)))
            if venue is None:
                return None
            self._ensure_scene_objects(session, venue)
            self._normalize_metric_scene_units(venue)
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def get_venue_snapshot(self, venue_id: str) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            self._ensure_scene_objects(session, venue)
            self._normalize_metric_scene_units(venue)
            session.refresh(venue)
            return self._snapshot_from_model(venue)

    def set_active_venue(self, venue_id: str) -> VenueSnapshot:
        with _session_scope() as session:
            venues = session.scalars(select(VenueModel)).all()
            target = None
            for venue in venues:
                is_target = venue.id == venue_id
                if venue.active != is_target:
                    venue.active = is_target
                    self._touch_venue(venue)
                if is_target:
                    target = venue
            if target is None:
                raise KeyError(f"Venue not found: {venue_id}")
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
            self._sync_legacy_scene_fields(venue)
            return self._snapshot_from_model(venue)

    def update_venue(self, venue_id: str, data: dict[str, object]) -> VenueSnapshot:
        with _session_scope() as session:
            venue = session.get(VenueModel, venue_id)
            if venue is None:
                raise KeyError(f"Venue not found: {venue_id}")
            self._ensure_scene_objects(session, venue)
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
                for other in session.scalars(select(VenueModel)).all():
                    other.active = other.id == venue.id
                    self._touch_venue(other)
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
            fixture = FixtureModel(
                id=str(fixture_data.get("id", uuid.uuid4())),
                venue_id=venue_id,
                order_index=next_order,
                fixture_type=str(fixture_data["fixture_type"]),
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
                is_manual=bool(fixture_data.get("is_manual", False)),
                address=int(fixture_data["address"]),
                universe=_normalize_universe(fixture_data.get("universe", "default")),
                x=float(fixture_data.get("x", 0.0)),
                y=float(fixture_data.get("y", 0.0)),
                z=float(fixture_data.get("z", 0.0)),
                rotation_x=float(fixture_data.get("rotation_x", 0.0)),
                rotation_y=float(fixture_data.get("rotation_y", 0.0)),
                rotation_z=float(fixture_data.get("rotation_z", 0.0)),
                options=dict(fixture_data.get("options", {})),
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

            if "options" in fixture_data:
                fixture.options = dict(fixture_data["options"])

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

    def ensure_seed_data(self) -> RuntimeBootstrap:
        for seed in build_seed_venues():
            self._upsert_seed(seed)
        return self.get_runtime_bootstrap()

    def _upsert_seed(self, seed: SeedVenueDefinition) -> None:
        with _session_scope() as session:
            venue = session.scalar(select(VenueModel).where(VenueModel.slug == seed.slug))
            if venue is None:
                venue = VenueModel(
                    slug=seed.slug,
                    name=seed.name,
                )
                session.add(venue)
                session.flush()

            venue.name = seed.name
            venue.archived = seed.archived
            venue.active = seed.active
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

            self._touch_venue(venue)

            if seed.active:
                for other in session.scalars(select(VenueModel)).all():
                    if other.id != venue.id and other.active:
                        other.active = False
                        self._touch_venue(other)

    def _touch_venue(self, venue: VenueModel) -> None:
        venue.revision = int(venue.revision) + 1
        venue.updated_at = datetime.utcnow()

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
                fixture_type=fixture.fixture_type,
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
                options=dict(fixture.options or {}),
            )
            for fixture in venue.fixtures
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
        )

    def _control_state_from_model(self, control_state: ControlStateModel) -> ControlState:
        return ControlState(
            mode=control_state.mode,
            vj_mode=control_state.vj_mode,
            theme_name=control_state.theme_name,
            manual_dimmer=control_state.manual_dimmer,
            hype_limiter=control_state.hype_limiter,
            show_waveform=control_state.show_waveform,
            show_fixture_mode=control_state.show_fixture_mode,
        )

    def _get_or_create_control_state(self, session) -> ControlStateModel:
        control_state = session.get(ControlStateModel, 1)
        if control_state is not None:
            return control_state

        initial_data = self._load_initial_control_state_data()
        control_state = ControlStateModel(
            id=1,
            mode=str(initial_data.get("mode", "chill")),
            vj_mode=str(initial_data.get("vj_mode", "full_rave")),
            theme_name=str(initial_data.get("theme_name", "Rave")),
            manual_dimmer=max(
                0.0, min(1.0, float(initial_data.get("manual_dimmer", 0.0)))
            ),
            hype_limiter=bool(initial_data.get("hype_limiter", False)),
            show_waveform=bool(initial_data.get("show_waveform", True)),
            show_fixture_mode=bool(initial_data.get("show_fixture_mode", False)),
        )
        session.add(control_state)
        session.flush()
        return control_state

    def _load_initial_control_state_data(self) -> dict[str, object]:
        state_path = get_repo_root() / "state.json"
        if not state_path.exists():
            return {}

        try:
            return dict(json.loads(state_path.read_text()))
        except Exception:
            return {}

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
            if scene_object is None:
                scene_object = SceneObjectModel(id=scene_object_spec.id, venue_id=venue.id)
                session.add(scene_object)
                venue.scene_objects.append(scene_object)
            if not scene_object.kind:
                scene_object.kind = scene_object_spec.kind
            if scene_object.id == scene_object_spec.id and scene_object.options in (None, {}):
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
                z=DJ_HEIGHT_METERS / 2.0,
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
