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
    assert len(bootstrap.active_venue.fixtures) >= 10
    assert bootstrap.control_state.mode == "chill"
    assert {scene_object.kind for scene_object in bootstrap.active_venue.scene_objects} == {
        "floor",
        "video_wall",
        "dj_table",
        "dj_cutout",
    }


def test_seed_is_idempotent(venue_repository):
    first_bootstrap = venue_repository.get_runtime_bootstrap()
    venue_repository.ensure_seed_data()
    second_bootstrap = venue_repository.get_runtime_bootstrap()

    assert len(first_bootstrap.venues) == len(second_bootstrap.venues)
    assert len(first_bootstrap.active_venue.fixtures) == len(
        second_bootstrap.active_venue.fixtures
    )


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
