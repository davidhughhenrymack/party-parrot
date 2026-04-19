from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_sock import Sock

from parrot_cloud.database import get_repo_root
from parrot_cloud.fixture_catalog import list_fixture_types
from parrot_cloud.repository import VenueRepository
from parrot_cloud.ws_hub import VenueUpdateHub
from parrot.director.frame import FrameSignal
from parrot.director.mode import MODES_BY_HYPE, Mode
from parrot.director.themes import themes
from parrot.utils.dmx_utils import Universe
from parrot.vj.vj_mode import VJMode


# Shift actions the remote control can trigger on the desktop director.
# Each target corresponds to a Director method: ``shift_<target>``.
SHIFT_TARGETS: tuple[str, ...] = ("lighting_only", "color_scheme", "vj_only")


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    sock = Sock(app)
    repository = VenueRepository()
    hub = VenueUpdateHub()

    app.config["venue_repository"] = repository
    app.config["venue_update_hub"] = hub

    @app.errorhandler(Exception)
    def _log_unhandled(err):
        # Force server-side traceback to stderr so 500s never go silent.
        print(
            f"[parrot_cloud] unhandled exception in {request.method} {request.path}:",
            file=sys.stderr,
        )
        traceback.print_exc()
        sys.stderr.flush()
        raise err

    def _safe_broadcast(label: str, build_event) -> None:
        """Broadcasts are informational side effects; never let them 500 the request."""
        try:
            hub.broadcast(build_event())
        except Exception:
            print(
                f"[parrot_cloud] broadcast {label} failed (ignored):",
                file=sys.stderr,
            )
            traceback.print_exc()
            sys.stderr.flush()

    def broadcast_bootstrap() -> None:
        _safe_broadcast(
            "bootstrap",
            lambda: {
                "type": "bootstrap",
                "data": repository.get_runtime_bootstrap().to_dict(),
            },
        )

    def broadcast_venues() -> None:
        _safe_broadcast(
            "venues",
            lambda: {
                "type": "venues",
                "data": {
                    "venues": [
                        summary.to_dict()
                        for summary in repository.list_venue_summaries()
                    ]
                },
            },
        )

    def broadcast_active_venue() -> None:
        venue = repository.get_active_venue_snapshot()
        if venue is None:
            return
        _safe_broadcast(
            "venue_snapshot",
            lambda: {"type": "venue_snapshot", "data": venue.to_dict()},
        )

    def broadcast_venue_snapshot(snapshot) -> None:
        _safe_broadcast(
            "venue_snapshot",
            lambda: {"type": "venue_snapshot", "data": snapshot.to_dict()},
        )

    def broadcast_control_state() -> None:
        _safe_broadcast(
            "control_state",
            lambda: {
                "type": "control_state",
                "data": repository.get_control_state().to_dict(),
            },
        )

    def broadcast_command(command_type: str, data: dict[str, object]) -> None:
        _safe_broadcast(
            command_type,
            lambda: {"type": command_type, "data": data},
        )

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
                "available_modes": [mode.name for mode in MODES_BY_HYPE],
                "available_vj_modes": [mode.value for mode in VJMode],
                "available_display_modes": ["venue", "dmx_heatmap", "vj"],
                "theme_names": [theme.name for theme in themes],
                "effects": [
                    FrameSignal.strobe.value,
                    FrameSignal.big_blinder.value,
                    FrameSignal.small_blinder.value,
                    FrameSignal.pulse.value,
                ],
                "shift_targets": list(SHIFT_TARGETS),
            }
        )

    @app.get("/api/bootstrap")
    def bootstrap():
        return jsonify(repository.get_runtime_bootstrap().to_dict())

    @app.get("/api/runtime/bootstrap")
    def runtime_bootstrap():
        return jsonify(repository.get_runtime_bootstrap().to_dict())

    @app.get("/api/runtime/fixture-state")
    def get_runtime_fixture_state():
        return jsonify(repository.get_fixture_runtime_state())

    @app.post("/api/runtime/fixture-state")
    def post_runtime_fixture_state():
        data = request.get_json(force=True) or {}
        payload = repository.set_fixture_runtime_state(dict(data))
        _safe_broadcast(
            "fixture_runtime_state",
            lambda: {"type": "fixture_runtime_state", "data": payload},
        )
        return jsonify(payload)

    @app.get("/api/runtime/vj-preview")
    def get_runtime_vj_preview():
        blob = repository.get_vj_preview_jpeg()
        if blob is None:
            return Response(status=404)
        return Response(blob, mimetype="image/jpeg")

    @app.post("/api/runtime/vj-preview")
    def post_runtime_vj_preview():
        raw = request.get_data()
        try:
            info = repository.set_vj_preview_jpeg(raw)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        _safe_broadcast(
            "vj_preview",
            lambda: {"type": "vj_preview", "data": info},
        )
        return jsonify(info)

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
        broadcast_venues()
        broadcast_active_venue()
        broadcast_control_state()
        return jsonify(control_state.to_dict())

    @app.get("/api/mode")
    def get_mode():
        control_state = repository.get_control_state()
        return jsonify(
            {
                "mode": control_state.mode,
                "available_modes": [mode.name for mode in MODES_BY_HYPE],
            }
        )

    @app.post("/api/mode")
    def set_mode():
        data = request.get_json(force=True)
        control_state = repository.update_control_state({"mode": data.get("mode")})
        broadcast_control_state()
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
        broadcast_control_state()
        return jsonify({"success": True, "vj_mode": control_state.vj_mode})

    @app.post("/api/effect")
    def trigger_effect():
        data = request.get_json(force=True) or {}
        effect = str(data.get("effect", ""))
        payload: dict[str, object] = {"effect": effect}
        if "value" in data:
            payload["value"] = float(data["value"])
        broadcast_command("effect", payload)
        return jsonify({"success": True, **payload})

    @app.post("/api/shift")
    def trigger_shift():
        data = request.get_json(force=True) or {}
        target = str(data.get("target", ""))
        if target not in SHIFT_TARGETS:
            return (
                jsonify(
                    {
                        "error": f"unknown shift target {target!r}",
                        "available_targets": list(SHIFT_TARGETS),
                    }
                ),
                400,
            )
        broadcast_command(f"shift_{target}", {"target": target})
        return jsonify({"success": True, "target": target})

    @app.post("/api/seed")
    def seed():
        payload = repository.ensure_seed_data().to_dict()
        broadcast_venues()
        broadcast_active_venue()
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
        broadcast_venues()
        broadcast_venue_snapshot(snapshot)
        return jsonify(snapshot.to_dict())

    @app.get("/api/venues/<venue_id>")
    def get_venue(venue_id: str):
        return jsonify(repository.get_venue_snapshot(venue_id).to_dict())

    @app.patch("/api/venues/<venue_id>")
    def patch_venue(venue_id: str):
        snapshot = repository.update_venue(venue_id, request.get_json(force=True))
        broadcast_venues()
        broadcast_venue_snapshot(snapshot)
        return jsonify(snapshot.to_dict())

    @app.post("/api/venues/<venue_id>/activate")
    def activate_venue(venue_id: str):
        snapshot = repository.set_active_venue(venue_id)
        broadcast_venues()
        broadcast_active_venue()
        broadcast_control_state()
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
        broadcast_venue_snapshot(snapshot)
        return jsonify(snapshot.to_dict())

    @app.patch("/api/venues/<venue_id>/scene-objects/<scene_object_kind>")
    def patch_scene_object(venue_id: str, scene_object_kind: str):
        snapshot = repository.update_scene_object(
            venue_id,
            scene_object_kind,
            request.get_json(force=True),
        )
        broadcast_venue_snapshot(snapshot)
        return jsonify(snapshot.to_dict())

    @app.post("/api/venues/<venue_id>/fixtures/magic-repatch")
    def magic_repatch_fixtures(venue_id: str):
        try:
            snapshot = repository.magic_repatch_fixtures_compact(venue_id)
        except KeyError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        broadcast_venue_snapshot(snapshot)
        return jsonify(snapshot.to_dict())

    @app.post("/api/venues/<venue_id>/fixtures")
    def create_fixture(venue_id: str):
        snapshot = repository.add_fixture(venue_id, request.get_json(force=True))
        broadcast_venue_snapshot(snapshot)
        return jsonify(snapshot.to_dict())

    @app.patch("/api/venues/<venue_id>/fixtures/<fixture_id>")
    def patch_fixture(venue_id: str, fixture_id: str):
        snapshot = repository.update_fixture(
            venue_id, fixture_id, request.get_json(force=True)
        )
        broadcast_venue_snapshot(snapshot)
        return jsonify(snapshot.to_dict())

    @app.delete("/api/venues/<venue_id>/fixtures/<fixture_id>")
    def remove_fixture(venue_id: str, fixture_id: str):
        snapshot = repository.delete_fixture(venue_id, fixture_id)
        broadcast_venue_snapshot(snapshot)
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
