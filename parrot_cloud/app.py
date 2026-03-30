from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_sock import Sock

from parrot_cloud.database import get_repo_root
from parrot_cloud.fixture_catalog import list_fixture_types
from parrot_cloud.repository import VenueRepository
from parrot_cloud.ws_hub import VenueUpdateHub
from parrot.director.frame import FrameSignal
from parrot.director.mode import Mode
from parrot.director.themes import themes
from parrot.utils.dmx_utils import Universe
from parrot.vj.vj_mode import VJMode


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    sock = Sock(app)
    repository = VenueRepository()
    hub = VenueUpdateHub()

    app.config["venue_repository"] = repository
    app.config["venue_update_hub"] = hub

    def broadcast_bootstrap() -> None:
        hub.broadcast(
            {
                "type": "bootstrap",
                "data": repository.get_runtime_bootstrap().to_dict(),
            }
        )

    def broadcast_command(command_type: str, data: dict[str, object]) -> None:
        hub.broadcast({"type": command_type, "data": data})

    def active_venue_supports_manual_dimmer() -> bool:
        active_venue = repository.get_active_venue_snapshot()
        if active_venue is None:
            return False
        return any(fixture.is_manual for fixture in active_venue.fixtures)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/<path:path>")
    def static_files(path: str):
        candidate = Path(app.static_folder, path)
        if candidate.exists() and candidate.is_file():
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.get("/api/assets/<path:filename>")
    def asset_file(filename: str):
        return send_from_directory(get_repo_root() / "assets", filename)

    @app.get("/api/config")
    def config():
        return jsonify(
            {
                "fixture_types": list_fixture_types(),
                "supported_universes": [
                    {"value": Universe.default.value, "label": "Enttec Pro"},
                    {"value": Universe.art1.value, "label": "Art-Net 1"},
                ],
                "available_modes": [mode.name for mode in Mode],
                "available_vj_modes": [mode.value for mode in VJMode],
                "theme_names": [theme.name for theme in themes],
                "effects": [
                    FrameSignal.strobe.value,
                    FrameSignal.big_blinder.value,
                    FrameSignal.small_blinder.value,
                    FrameSignal.pulse.value,
                ],
            }
        )

    @app.get("/api/bootstrap")
    def bootstrap():
        return jsonify(repository.get_runtime_bootstrap().to_dict())

    @app.get("/api/runtime/bootstrap")
    def runtime_bootstrap():
        return jsonify(repository.get_runtime_bootstrap().to_dict())

    @app.get("/api/runtime/active-venue")
    def runtime_active_venue():
        venue = repository.get_active_venue_snapshot()
        return jsonify(None if venue is None else venue.to_dict())

    @app.get("/api/control-state")
    def get_control_state():
        control_state = repository.get_control_state()
        return jsonify(control_state.to_dict())

    @app.patch("/api/control-state")
    def patch_control_state():
        control_state = repository.update_control_state(request.get_json(force=True))
        broadcast_bootstrap()
        return jsonify(control_state.to_dict())

    @app.get("/api/mode")
    def get_mode():
        control_state = repository.get_control_state()
        return jsonify(
            {
                "mode": control_state.mode,
                "available_modes": [mode.name for mode in Mode],
            }
        )

    @app.post("/api/mode")
    def set_mode():
        data = request.get_json(force=True)
        control_state = repository.update_control_state({"mode": data.get("mode")})
        broadcast_bootstrap()
        return jsonify({"success": True, "mode": control_state.mode})

    @app.get("/api/vj_mode")
    def get_vj_mode():
        control_state = repository.get_control_state()
        return jsonify(
            {
                "vj_mode": control_state.vj_mode,
                "available_vj_modes": [mode.value for mode in VJMode],
            }
        )

    @app.post("/api/vj_mode")
    def set_vj_mode():
        data = request.get_json(force=True)
        control_state = repository.update_control_state({"vj_mode": data.get("vj_mode")})
        broadcast_bootstrap()
        return jsonify({"success": True, "vj_mode": control_state.vj_mode})

    @app.get("/api/manual_dimmer")
    def get_manual_dimmer():
        control_state = repository.get_control_state()
        return jsonify(
            {
                "value": control_state.manual_dimmer,
                "supported": active_venue_supports_manual_dimmer(),
            }
        )

    @app.post("/api/manual_dimmer")
    def set_manual_dimmer():
        data = request.get_json(force=True)
        control_state = repository.update_control_state(
            {"manual_dimmer": data.get("value", 0.0)}
        )
        broadcast_bootstrap()
        return jsonify({"success": True, "value": control_state.manual_dimmer})

    @app.post("/api/effect")
    def trigger_effect():
        data = request.get_json(force=True)
        effect = str(data.get("effect", ""))
        broadcast_command("effect", {"effect": effect})
        return jsonify({"success": True, "effect": effect})

    @app.post("/api/seed")
    def seed():
        payload = repository.ensure_seed_data().to_dict()
        broadcast_bootstrap()
        return jsonify(payload)

    @app.get("/api/fixture-types")
    def fixture_types():
        return jsonify({"fixture_types": list_fixture_types()})

    @app.get("/api/venues")
    def list_venues():
        return jsonify(
            {"venues": [summary.to_dict() for summary in repository.list_venue_summaries()]}
        )

    @app.post("/api/venues")
    def create_venue():
        data = request.get_json(force=True)
        snapshot = repository.create_venue(str(data.get("name", "New Venue")))
        broadcast_bootstrap()
        return jsonify(snapshot.to_dict())

    @app.get("/api/venues/<venue_id>")
    def get_venue(venue_id: str):
        return jsonify(repository.get_venue_snapshot(venue_id).to_dict())

    @app.patch("/api/venues/<venue_id>")
    def patch_venue(venue_id: str):
        snapshot = repository.update_venue(venue_id, request.get_json(force=True))
        broadcast_bootstrap()
        return jsonify(snapshot.to_dict())

    @app.post("/api/venues/<venue_id>/activate")
    def activate_venue(venue_id: str):
        snapshot = repository.set_active_venue(venue_id)
        broadcast_bootstrap()
        return jsonify(snapshot.to_dict())

    @app.patch("/api/venues/<venue_id>/video-wall")
    def patch_video_wall(venue_id: str):
        payload = request.get_json(force=True)
        snapshot = repository.update_video_wall(
            venue_id,
            {
                "video_wall_x": payload.get("x"),
                "video_wall_y": payload.get("y"),
                "video_wall_z": payload.get("z"),
                "video_wall_width": payload.get("width"),
                "video_wall_height": payload.get("height"),
                "video_wall_depth": payload.get("depth"),
                "video_wall_locked": payload.get("locked"),
            },
        )
        broadcast_bootstrap()
        return jsonify(snapshot.to_dict())

    @app.post("/api/venues/<venue_id>/fixtures")
    def create_fixture(venue_id: str):
        snapshot = repository.add_fixture(venue_id, request.get_json(force=True))
        broadcast_bootstrap()
        return jsonify(snapshot.to_dict())

    @app.patch("/api/venues/<venue_id>/fixtures/<fixture_id>")
    def patch_fixture(venue_id: str, fixture_id: str):
        snapshot = repository.update_fixture(
            venue_id, fixture_id, request.get_json(force=True)
        )
        broadcast_bootstrap()
        return jsonify(snapshot.to_dict())

    @app.delete("/api/venues/<venue_id>/fixtures/<fixture_id>")
    def remove_fixture(venue_id: str, fixture_id: str):
        snapshot = repository.delete_fixture(venue_id, fixture_id)
        broadcast_bootstrap()
        return jsonify(snapshot.to_dict())

    @sock.route("/ws/venue-updates")
    def venue_updates(ws):
        hub.add_client(ws)
        try:
            ws.send(
                json.dumps(
                    {
                        "type": "bootstrap",
                        "data": repository.get_runtime_bootstrap().to_dict(),
                    }
                )
            )
            while True:
                if ws.receive() is None:
                    break
        finally:
            hub.remove_client(ws)

    return app
