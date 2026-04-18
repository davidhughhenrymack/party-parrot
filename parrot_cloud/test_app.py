import pytest

from parrot_cloud.app import create_app
from parrot_cloud.database import reset_database_state
from parrot_cloud.management import initialize_database


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "parrot_cloud.sqlite3"
    monkeypatch.setenv("PARROT_CLOUD_DB_PATH", str(db_path))
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
    assert data["fixture_runtime_state"]["version"] == 1
    assert data["fixture_runtime_state"]["fixtures"] == []
    assert data.get("vj_preview") is None
    assert {scene_object["kind"] for scene_object in data["active_venue"]["scene_objects"]} == {
        "floor",
        "video_wall",
        "dj_table",
        "dj_cutout",
    }


def test_runtime_fixture_state_post_broadcast_shape(client):
    response = client.post(
        "/api/runtime/fixture-state",
        json={
            "version": 1,
            "fixtures": [
                {
                    "id": "test-fixture",
                    "dimmer": 0.5,
                    "rgb": [1.0, 0.0, 0.0],
                    "pan_deg": 10.0,
                    "tilt_deg": -5.0,
                }
            ],
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["fixtures"][0]["id"] == "test-fixture"
    assert data["fixtures"][0]["dimmer"] == 0.5


def test_runtime_vj_preview_post_and_get(client):
    from io import BytesIO

    from PIL import Image

    img = Image.new("RGB", (8, 8), color=(10, 200, 30))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    jpeg = buf.getvalue()
    post = client.post(
        "/api/runtime/vj-preview",
        data=jpeg,
        headers={"Content-Type": "image/jpeg"},
    )
    assert post.status_code == 200
    assert "updated_at" in post.get_json()
    get_img = client.get("/api/runtime/vj-preview")
    assert get_img.status_code == 200
    assert get_img.mimetype == "image/jpeg"
    assert len(get_img.data) >= len(jpeg) // 2
    boot = client.get("/api/bootstrap").get_json()
    assert boot["vj_preview"] is not None
    assert boot["vj_preview"]["updated_at"] is not None


def test_runtime_fixture_state_get_returns_current(client):
    client.post(
        "/api/runtime/fixture-state",
        json={
            "version": 1,
            "fixtures": [{"id": "a", "dimmer": 1.0, "rgb": [0.0, 1.0, 0.0]}],
        },
    )
    response = client.get("/api/runtime/fixture-state")
    assert response.status_code == 200
    data = response.get_json()
    assert data["version"] == 1
    assert len(data["fixtures"]) == 1
    assert data["fixtures"][0]["id"] == "a"


def test_fixture_types_endpoint(client):
    response = client.get("/api/fixture-types")

    assert response.status_code == 200
    data = response.get_json()
    par_rgb = next(item for item in data["fixture_types"] if item["key"] == "par_rgb")
    assert par_rgb["dmx_address_width"] == 7


def test_dmx_address_width_for_fixture_helper():
    from parrot_cloud.fixture_catalog import dmx_address_width_for_fixture

    assert dmx_address_width_for_fixture("par_rgb", {}) == 7
    assert dmx_address_width_for_fixture("manual_dimmer_channel", {"width": 4}) == 4
    assert dmx_address_width_for_fixture("motionstrip_38", {}) == 38
    assert dmx_address_width_for_fixture("mirrorball", {}) == 1


def test_asset_endpoint_serves_dj_silhouette(client):
    response = client.get("/api/assets/dj.png")

    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_config_endpoint_lists_supported_universes(client):
    response = client.get("/api/config")

    assert response.status_code == 200
    data = response.get_json()
    assert data["supported_universes"] == [
        {"value": "default", "label": "Enttec Pro"},
        {"value": "art1", "label": "Art-Net 1"},
    ]
    assert "chill" in data["available_modes"]
    assert "prom_dmack" in data["available_vj_modes"]
    assert "prom_wufky" in data["available_vj_modes"]
    assert "prom_mayhem" in data["available_vj_modes"]
    assert "prom_thunderbunny" in data["available_vj_modes"]
    assert data["available_display_modes"] == ["venue", "dmx_heatmap", "vj"]
    assert data["shift_targets"] == ["lighting_only", "color_scheme", "vj_only"]


def test_shift_endpoint_accepts_known_targets(client):
    for target in ("lighting_only", "color_scheme", "vj_only"):
        response = client.post("/api/shift", json={"target": target})
        assert response.status_code == 200
        assert response.get_json() == {"success": True, "target": target}


def test_shift_endpoint_rejects_unknown_target(client):
    response = client.post("/api/shift", json={"target": "nope"})
    assert response.status_code == 400
    body = response.get_json()
    assert "error" in body
    assert body["available_targets"] == ["lighting_only", "color_scheme", "vj_only"]


def test_control_state_endpoints(client):
    bootstrap = client.get("/api/bootstrap").get_json()
    new_active_venue_id = bootstrap["active_venue"]["summary"]["id"]
    response = client.patch(
        "/api/control-state",
        json={
            "mode": "rave",
            "display_mode": "venue",
            "active_venue_id": new_active_venue_id,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["mode"] == "rave"
    assert response.get_json()["display_mode"] == "venue"
    assert response.get_json()["active_venue_id"] == new_active_venue_id

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


def test_magic_repatch_fixtures_compact(client):
    created = client.post("/api/venues", json={"name": "Magic Repatch Venue"})
    assert created.status_code == 200
    venue_id = created.get_json()["summary"]["id"]

    client.post(
        f"/api/venues/{venue_id}/fixtures",
        json={
            "id": "repatch-a",
            "fixture_type": "par_rgb",
            "address": 90,
            "universe": "default",
            "x": 1.0,
            "y": 2.0,
            "z": 3.0,
            "options": {},
        },
    )
    client.post(
        f"/api/venues/{venue_id}/fixtures",
        json={
            "id": "repatch-b",
            "fixture_type": "par_rgb",
            "address": 400,
            "universe": "default",
            "x": 2.0,
            "y": 2.0,
            "z": 3.0,
            "options": {},
        },
    )

    repatch = client.post(f"/api/venues/{venue_id}/fixtures/magic-repatch")
    assert repatch.status_code == 200
    fixtures = repatch.get_json()["fixtures"]
    by_id = {f["id"]: f for f in fixtures}
    assert by_id["repatch-a"]["address"] == 1
    assert by_id["repatch-b"]["address"] == 8


def test_scene_object_patch_endpoint(client):
    bootstrap = client.get("/api/bootstrap").get_json()
    venue_id = bootstrap["active_venue"]["summary"]["id"]

    response = client.patch(
        f"/api/venues/{venue_id}/scene-objects/dj_table",
        json={"x": 42.0, "y": 24.0, "z": 3.5},
    )

    assert response.status_code == 200
    dj_table = next(
        scene_object
        for scene_object in response.get_json()["scene_objects"]
        if scene_object["kind"] == "dj_table"
    )
    assert dj_table["x"] == 42.0
    assert dj_table["y"] == 24.0
    assert dj_table["z"] == 3.5


def test_patch_video_wall_does_not_reset_dj_table_position(client):
    bootstrap = client.get("/api/bootstrap").get_json()
    venue_id = bootstrap["active_venue"]["summary"]["id"]

    client.patch(
        f"/api/venues/{venue_id}/scene-objects/dj_table",
        json={"x": 1.25, "y": -4.5, "z": 0.9},
    )

    wall = client.patch(
        f"/api/venues/{venue_id}/video-wall",
        json={"y": -6.0, "z": 3.2},
    )
    assert wall.status_code == 200
    data = wall.get_json()
    dj = next(o for o in data["scene_objects"] if o["kind"] == "dj_table")
    assert dj["x"] == 1.25
    assert dj["y"] == -4.5
    assert dj["z"] == 0.9


def test_fixture_group_name_sets_runtime_fixture_group_key(client):
    """group_name on fixtures is how the desktop builds FixtureGroup; API must persist it."""
    created = client.post("/api/venues", json={"name": "Group Name Venue"})
    assert created.status_code == 200
    venue_id = created.get_json()["summary"]["id"]

    a = client.post(
        f"/api/venues/{venue_id}/fixtures",
        json={
            "id": "g-a",
            "fixture_type": "par_rgb",
            "address": 1,
            "universe": "default",
            "x": 1.0,
            "y": 2.0,
            "z": 3.0,
            "options": {},
        },
    )
    b = client.post(
        f"/api/venues/{venue_id}/fixtures",
        json={
            "id": "g-b",
            "fixture_type": "par_rgb",
            "address": 5,
            "universe": "default",
            "x": 2.0,
            "y": 2.0,
            "z": 3.0,
            "options": {},
        },
    )
    assert a.status_code == 200
    assert b.status_code == 200

    pa = client.patch(
        f"/api/venues/{venue_id}/fixtures/g-a",
        json={"group_name": "Front wash"},
    )
    pb = client.patch(
        f"/api/venues/{venue_id}/fixtures/g-b",
        json={"group_name": "Front wash"},
    )
    assert pa.status_code == 200
    assert pb.status_code == 200
    snap = client.get(f"/api/venues/{venue_id}").get_json()
    by_id = {f["id"]: f for f in snap["fixtures"]}
    assert by_id["g-a"]["group_name"] == "Front wash"
    assert by_id["g-b"]["group_name"] == "Front wash"
