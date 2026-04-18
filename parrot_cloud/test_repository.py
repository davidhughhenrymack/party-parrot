import pytest

from parrot_cloud.database import reset_database_state
from parrot_cloud.management import run_migrations
from parrot_cloud.repository import VenueRepository


@pytest.fixture
def venue_repository(monkeypatch, tmp_path):
    db_path = tmp_path / "parrot_cloud.sqlite3"
    monkeypatch.setenv("PARROT_CLOUD_DB_PATH", str(db_path))
    reset_database_state()
    run_migrations()
    repository = VenueRepository()
    repository.ensure_seed_data()
    yield repository
    reset_database_state()


def test_seed_creates_demo_venue(venue_repository):
    bootstrap = venue_repository.get_runtime_bootstrap()

    assert bootstrap.active_venue is not None
    assert bootstrap.active_venue.summary.slug == "mtn-lotus-demo"
    assert len(bootstrap.active_venue.fixtures) == 0
    assert bootstrap.control_state.mode == "chill"
    assert {scene_object.kind for scene_object in bootstrap.active_venue.scene_objects} == {
        "floor",
        "video_wall",
        "dj_table",
        "dj_cutout",
    }
    assert bootstrap.vj_preview is None


def test_seed_is_idempotent(venue_repository):
    first_bootstrap = venue_repository.get_runtime_bootstrap()
    venue_repository.ensure_seed_data()
    second_bootstrap = venue_repository.get_runtime_bootstrap()

    assert len(first_bootstrap.venues) == len(second_bootstrap.venues)
    assert len(first_bootstrap.active_venue.fixtures) == len(
        second_bootstrap.active_venue.fixtures
    )


def test_manual_dimmer_channel_fixture_gets_is_manual(venue_repository):
    active_snapshot = venue_repository.get_active_venue_snapshot()
    created = venue_repository.add_fixture(
        active_snapshot.summary.id,
        {
            "fixture_type": "manual_dimmer_channel",
            "address": 1,
            "universe": "default",
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "rotation_x": 0.0,
            "rotation_y": 0.0,
            "rotation_z": 0.0,
            "options": {},
        },
    )
    manual = next(
        f for f in created.fixtures if f.fixture_type == "manual_dimmer_channel"
    )
    assert manual.is_manual is True


def test_fixture_crud_updates_snapshot(venue_repository):
    active_snapshot = venue_repository.get_active_venue_snapshot()

    created_snapshot = venue_repository.add_fixture(
        active_snapshot.summary.id,
        {
            "id": "integration-test-fixture",
            "fixture_type": "par_rgb",
            "address": 401,
            "universe": "default",
            "x": 12.0,
            "y": 34.0,
            "z": 5.0,
            "rotation_x": 0.1,
            "rotation_y": 0.0,
            "rotation_z": 0.0,
            "options": {},
        },
    )
    assert any(fixture.id == "integration-test-fixture" for fixture in created_snapshot.fixtures)

    updated_snapshot = venue_repository.update_fixture(
        active_snapshot.summary.id,
        "integration-test-fixture",
        {"address": 402, "x": 44.0},
    )
    updated_fixture = next(
        fixture
        for fixture in updated_snapshot.fixtures
        if fixture.id == "integration-test-fixture"
    )
    assert updated_fixture.address == 402
    assert updated_fixture.x == 44.0

    deleted_snapshot = venue_repository.delete_fixture(
        active_snapshot.summary.id,
        "integration-test-fixture",
    )
    assert not any(
        fixture.id == "integration-test-fixture" for fixture in deleted_snapshot.fixtures
    )


def test_video_wall_update_does_not_reset_dj_table_scene_object(venue_repository):
    bootstrap = venue_repository.get_runtime_bootstrap()
    venue_id = bootstrap.active_venue.summary.id

    moved = venue_repository.update_scene_object(
        venue_id,
        "dj_table",
        {
            "x": 5.5,
            "y": -3.25,
            "z": 1.05,
            "rotation_x": 0.0,
            "rotation_y": 0.0,
            "rotation_z": 0.1,
        },
    )
    dj_before = next(o for o in moved.scene_objects if o.kind == "dj_table")
    assert dj_before.x == 5.5
    assert dj_before.y == -3.25

    after_wall = venue_repository.update_video_wall(
        venue_id,
        {"video_wall_y": -7.5},
    )
    dj_after = next(o for o in after_wall.scene_objects if o.kind == "dj_table")
    assert dj_after.x == dj_before.x
    assert dj_after.y == dj_before.y
    assert dj_after.z == dj_before.z
    assert dj_after.rotation_z == dj_before.rotation_z


def test_active_venue_persists_across_seed_runs(venue_repository):
    bootstrap = venue_repository.get_runtime_bootstrap()
    demo_id = bootstrap.active_venue.summary.id
    other = venue_repository.create_venue("Other Hall")
    other_id = other.summary.id
    assert other_id != demo_id

    venue_repository.update_control_state({"active_venue_id": other_id})

    venue_repository.ensure_seed_data()

    after = venue_repository.get_runtime_bootstrap()
    assert after.control_state.active_venue_id == other_id
    assert after.active_venue is not None
    assert after.active_venue.summary.id == other_id


def test_moving_head_add_seeds_pan_tilt_range_defaults(venue_repository):
    """A new Hybrid 140SR fixture gets the fixture-type's mechanical range in options."""
    active = venue_repository.get_active_venue_snapshot()
    created = venue_repository.add_fixture(
        active.summary.id,
        {
            "id": "range-seed-hybrid",
            "fixture_type": "chauvet_intimidator_hybrid_140sr",
            "address": 100,
            "universe": "default",
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
    )
    fixture = next(f for f in created.fixtures if f.id == "range-seed-hybrid")
    assert fixture.options["pan_lower"] == 0
    assert fixture.options["pan_upper"] == 540
    assert fixture.options["tilt_lower"] == 0
    assert fixture.options["tilt_upper"] == 270


def test_moving_head_add_respects_client_range_override(venue_repository):
    active = venue_repository.get_active_venue_snapshot()
    created = venue_repository.add_fixture(
        active.summary.id,
        {
            "id": "range-override",
            "fixture_type": "chauvet_spot_160",
            "address": 200,
            "universe": "default",
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            # Top-level override wins over the fixture-type default (360..540).
            "pan_lower": 400,
            "pan_upper": 500,
        },
    )
    fixture = next(f for f in created.fixtures if f.id == "range-override")
    assert fixture.options["pan_lower"] == 400
    assert fixture.options["pan_upper"] == 500
    # Tilt defaults still seeded from the type.
    assert fixture.options["tilt_lower"] == 0
    assert fixture.options["tilt_upper"] == 90


def test_update_fixture_merges_top_level_pan_tilt_range(venue_repository):
    """PATCHing a single range field must preserve other options and the unchanged range fields."""
    active = venue_repository.get_active_venue_snapshot()
    created = venue_repository.add_fixture(
        active.summary.id,
        {
            "id": "range-merge",
            "fixture_type": "chauvet_intimidator_hybrid_140sr",
            "address": 1,
            "universe": "default",
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "options": {"pan_lower": 100, "pan_upper": 400, "custom_marker": "keep me"},
        },
    )
    fixture = next(f for f in created.fixtures if f.id == "range-merge")
    # Client-supplied options win where they overlap with the type defaults;
    # unspecified keys (tilt_*) fall through to the fixture-type defaults so new
    # fixtures always expose the full range for editing.
    assert fixture.options["pan_lower"] == 100
    assert fixture.options["pan_upper"] == 400
    assert fixture.options["custom_marker"] == "keep me"
    assert fixture.options["tilt_lower"] == 0
    assert fixture.options["tilt_upper"] == 270

    updated = venue_repository.update_fixture(
        active.summary.id,
        "range-merge",
        {"pan_lower": 250},
    )
    fixture = next(f for f in updated.fixtures if f.id == "range-merge")
    # pan_lower was patched; everything else (including the unrelated custom_marker)
    # is untouched.
    assert fixture.options["pan_lower"] == 250
    assert fixture.options["pan_upper"] == 400
    assert fixture.options["custom_marker"] == "keep me"
    assert fixture.options["tilt_lower"] == 0
    assert fixture.options["tilt_upper"] == 270


def test_legacy_moving_head_reads_get_pan_tilt_range_defaults(venue_repository):
    """Fixtures stored before the pan/tilt range feature existed must read as defaults.

    We simulate a legacy row by inserting a moving head with an ``options`` blob
    that doesn't include any pan/tilt range keys, then reading the venue back
    and asserting the UI sees the fixture-type defaults rather than zeros.
    """
    from parrot_cloud.database import create_session
    from parrot_cloud.models import FixtureModel

    active = venue_repository.get_active_venue_snapshot()
    created = venue_repository.add_fixture(
        active.summary.id,
        {
            "id": "legacy-hybrid",
            "fixture_type": "chauvet_intimidator_hybrid_140sr",
            "address": 300,
            "universe": "default",
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
    )
    assert any(f.id == "legacy-hybrid" for f in created.fixtures)

    # Drop the range keys from the DB row to mimic a pre-feature fixture.
    session = create_session()
    try:
        row = session.get(FixtureModel, "legacy-hybrid")
        assert row is not None
        row.options = {"custom_marker": "legacy"}
        session.commit()
    finally:
        session.close()

    after = venue_repository.get_active_venue_snapshot()
    legacy = next(f for f in after.fixtures if f.id == "legacy-hybrid")
    assert legacy.options["custom_marker"] == "legacy"
    assert legacy.options["pan_lower"] == 0
    assert legacy.options["pan_upper"] == 540
    assert legacy.options["tilt_lower"] == 0
    assert legacy.options["tilt_upper"] == 270


def test_non_moving_head_add_does_not_seed_pan_tilt_range(venue_repository):
    active = venue_repository.get_active_venue_snapshot()
    created = venue_repository.add_fixture(
        active.summary.id,
        {
            "id": "par-no-range",
            "fixture_type": "par_rgb",
            "address": 1,
            "universe": "default",
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
    )
    fixture = next(f for f in created.fixtures if f.id == "par-no-range")
    assert "pan_lower" not in fixture.options
    assert "tilt_upper" not in fixture.options


def test_initial_control_state_tracks_active_seed_venue(monkeypatch, tmp_path):
    db_path = tmp_path / "parrot_cloud.sqlite3"
    monkeypatch.setenv("PARROT_CLOUD_DB_PATH", str(db_path))
    reset_database_state()
    run_migrations()
    repository = VenueRepository()
    repository.ensure_seed_data()
    control_state = repository.get_control_state()

    active_venue = repository.get_active_venue_snapshot()
    assert active_venue is not None
    assert control_state.active_venue_id == active_venue.summary.id
    assert control_state.display_mode == "dmx_heatmap"
