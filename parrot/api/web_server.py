import os
import socket
import threading
import logging
from flask import Flask, jsonify, request, send_from_directory
from parrot.director.mode import MODES_BY_HYPE, Mode
from parrot.vj.vj_mode import VJMode
from parrot.state import State

# Create Flask app
app = Flask(__name__)

# Global reference to the state object
state_instance = None
editor_port_value = 4041


def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Create a socket to determine the local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't need to be reachable
        s.connect(("8.8.8.8", 1))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"  # Fallback to localhost


@app.route("/api/mode", methods=["GET"])
def get_mode():
    """Get the current mode."""
    available_modes = [p.name for p in MODES_BY_HYPE]
    if state_instance and state_instance.mode:
        return jsonify(
            {
                "mode": state_instance.mode.name,
                "available_modes": available_modes,
            }
        )
    return jsonify({"mode": None, "available_modes": available_modes})


@app.route("/api/mode", methods=["POST"])
def set_mode():
    """Set the current mode."""
    if not state_instance:
        return jsonify({"error": "State not initialized"}), 500

    data = request.json
    if not data or "mode" not in data:
        return jsonify({"error": "Missing mode parameter"}), 400

    mode_name = data["mode"]
    try:
        mode = Mode[mode_name]

        # Return success immediately to make the web UI responsive
        response = jsonify({"success": True, "mode": mode.name})

        # Use the thread-safe method to set the mode (after preparing the response)
        state_instance.set_mode_thread_safe(mode)

        return response
    except KeyError:
        return (
            jsonify(
                {
                    "error": f"Invalid mode: {mode_name}. Available modes: {[p.name for p in Mode]}"
                }
            ),
            400,
        )


@app.route("/")
def index():
    """Serve the main HTML page."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(current_dir, "static")
    return send_from_directory(static_dir, "index.html")


@app.route("/<path:path>")
def static_files(path):
    """Serve static files."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(current_dir, "static")
    return send_from_directory(static_dir, path)


@app.route("/api/manual_fixture_dimmers", methods=["POST"])
def merge_manual_fixture_dimmers():
    """Merge per-fixture manual dimmer levels (0–1) by cloud fixture id."""
    if not state_instance:
        return jsonify({"success": False, "error": "State not initialized"}), 400
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Expected JSON object"}), 400
    patch_raw = data.get("patch", data)
    if not isinstance(patch_raw, dict):
        return jsonify({"success": False, "error": "patch must be an object"}), 400
    try:
        patch = {str(k): float(v) for k, v in patch_raw.items()}
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid dimmer values"}), 400
    state_instance.merge_manual_fixture_dimmers(patch)
    return jsonify(
        {
            "success": True,
            "manual_fixture_dimmers": dict(state_instance.manual_fixture_dimmers),
        }
    )


@app.route("/api/effect", methods=["POST"])
def set_effect():
    """Set the current effect."""
    if not state_instance:
        return jsonify({"error": "State not initialized"}), 500

    data = request.json
    if not data or "effect" not in data:
        return jsonify({"error": "Missing effect parameter"}), 400

    effect = data["effect"]
    try:
        # Return success immediately to make the web UI responsive
        response = jsonify({"success": True, "effect": effect})

        # Use the thread-safe method to set the effect (after preparing the response)
        state_instance.set_effect_thread_safe(effect)

        return response
    except Exception as e:
        return jsonify({"error": f"Error setting effect: {str(e)}"}), 500


@app.route("/api/vj_mode", methods=["GET"])
def get_vj_mode():
    """Get the current VJ mode."""
    if state_instance and state_instance.vj_mode:
        return jsonify(
            {
                "vj_mode": state_instance.vj_mode.name,
                "available_vj_modes": [mode.name for mode in VJMode],
            }
        )
    return jsonify(
        {"vj_mode": None, "available_vj_modes": [mode.name for mode in VJMode]}
    )


@app.route("/api/vj_mode", methods=["POST"])
def set_vj_mode():
    """Set the current VJ mode."""
    if not state_instance:
        return jsonify({"error": "State not initialized"}), 500

    data = request.json
    if not data or "vj_mode" not in data:
        return jsonify({"error": "Missing vj_mode parameter"}), 400

    vj_mode_name = data["vj_mode"]
    try:
        vj_mode = VJMode[vj_mode_name]

        # Return success immediately to make the web UI responsive
        response = jsonify({"success": True, "vj_mode": vj_mode.name})

        # Use the thread-safe method to set the VJ mode (after preparing the response)
        state_instance.set_vj_mode_thread_safe(vj_mode)

        return response
    except KeyError:
        return (
            jsonify(
                {
                    "error": f"Invalid vj_mode: {vj_mode_name}. Available modes: {[mode.name for mode in VJMode]}"
                }
            ),
            400,
        )


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify({"editor_port": editor_port_value})


def start_web_server(
    state,
    host="0.0.0.0",
    port=5000,
    threaded=True,
    editor_port=4041,
):
    """Start the web server in a separate thread or return the app for main thread integration."""
    global state_instance, editor_port_value
    state_instance = state
    editor_port_value = editor_port

    # Suppress Flask/Werkzeug logs
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.logger.setLevel(logging.ERROR)

    if threaded:
        # Start Flask in a separate thread (legacy mode)
        threading.Thread(
            target=lambda: app.run(
                host=host, port=port, debug=False, use_reloader=False
            ),
            daemon=True,
        ).start()
        return None
    else:
        # Return app and server for main thread integration
        from werkzeug.serving import make_server

        server = make_server(host, port, app, threaded=False)
        return server
