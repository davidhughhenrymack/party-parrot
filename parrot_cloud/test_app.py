import pytest

from parrot_cloud.app import create_app
from parrot_cloud.database import reset_database_state
from parrot_cloud.management import initialize_database


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "parrot_cloud.sqlite3"
    monkeypatch.setenv("PARROT_CLOUD_DB_PATH", str(db_path))
    monkeypatch.setattr("parrot_cloud.repository.get_repo_root", lambda: tmp_path)
    reset_database_state()
    initialize_database()
    app = create_app()
    app.config["TESTING"] = True
    yield app.test_client()
    reset_database_state()


def test_bootstrap_endpoint_returns_active_venue(client):
    response = client.get("/api/bootstrap")

    assert response.status_code == 200
    data = response.get_json()
    assert data["active_venue"]["summary"]["slug"] == "mtn-lotus-demo"
    assert data["control_state"]["mode"] == "chill"
    assert {scene_object["kind"] for scene_object in data["active_venue"]["scene_objects"]} == {
        "floor",
        "video_wall",
        "dj_table",
        "dj_cutout",
    }


def test_fixture_types_endpoint(client):
    response = client.get("/api/fixture-types")

    assert response.status_code == 200
    data = response.get_json()
    assert any(item["key"] == "par_rgb" for item in data["fixture_types"])


def test_config_endpoint_lists_supported_universes(client):
    response = client.get("/api/config")

    assert response.status_code == 200
    data = response.get_json()
    assert data["supported_universes"] == [
        {"value": "default", "label": "Enttec Pro"},
        {"value": "art1", "label": "Art-Net 1"},
    ]
    assert "chill" in data["available_modes"]
    assert "full_rave" in data["available_vj_modes"]


def test_control_state_endpoints(client):
    response = client.patch(
        "/api/control-state",
        json={"mode": "rave", "manual_dimmer": 0.25},
    )

    assert response.status_code == 200
    assert response.get_json()["mode"] == "rave"
    assert response.get_json()["manual_dimmer"] == 0.25

    mode_response = client.get("/api/mode")
    assert mode_response.get_json()["mode"] == "rave"


def test_venue_crud_endpoint_flow(client):
    created = client.post("/api/venues", json={"name": "Warehouse Test"})
    assert created.status_code == 200
    venue_id = created.get_json()["summary"]["id"]

    renamed = client.patch(f"/api/venues/{venue_id}", json={"name": "Warehouse Prime"})
    assert renamed.status_code == 200
    assert renamed.get_json()["summary"]["name"] == "Warehouse Prime"

    activated = client.post(f"/api/venues/{venue_id}/activate")
    assert activated.status_code == 200
    assert activated.get_json()["summary"]["active"] is True


def test_video_wall_and_fixture_endpoints(client):
    bootstrap = client.get("/api/bootstrap").get_json()
    venue_id = bootstrap["active_venue"]["summary"]["id"]

    wall_response = client.patch(
        f"/api/venues/{venue_id}/video-wall",
        json={"x": 25.0, "y": 30.0, "z": 12.0, "locked": True},
    )
    assert wall_response.status_code == 200
    assert wall_response.get_json()["video_wall"]["locked"] is True

    fixture_response = client.post(
        f"/api/venues/{venue_id}/fixtures",
        json={
            "id": "app-test-fixture",
            "fixture_type": "par_rgb",
            "address": 410,
            "universe": "art1",
            "x": 5.0,
            "y": 6.0,
            "z": 7.0,
            "options": {},
        },
    )
    assert fixture_response.status_code == 200
    fixture = next(
        fixture
        for fixture in fixture_response.get_json()["fixtures"]
        if fixture["id"] == "app-test-fixture"
    )
    assert fixture["universe"] == "art1"

    patch_response = client.patch(
        f"/api/venues/{venue_id}/fixtures/app-test-fixture",
        json={"address": 411, "universe": "default"},
    )
    assert patch_response.status_code == 200
    patched_fixture = next(
        fixture
        for fixture in patch_response.get_json()["fixtures"]
        if fixture["id"] == "app-test-fixture"
    )
    assert patched_fixture["address"] == 411
    assert patched_fixture["universe"] == "default"
