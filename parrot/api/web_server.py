import os
import socket
import threading
import time
import logging
from flask import Flask, jsonify, request, send_from_directory
from parrot.director.mode import Mode
from parrot.vj.vj_mode import VJMode
from parrot.state import State
from parrot.patch_bay import has_manual_dimmer

# Create Flask app
app = Flask(__name__)

# Global reference to the state object
state_instance = None
# Global reference to the director object
director_instance = None
# Track when hype was last deployed
last_hype_time = 0
# How long hype lasts (in seconds)
HYPE_DURATION = 8


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
    if state_instance and state_instance.mode:
        return jsonify(
            {
                "mode": state_instance.mode.name,
                "available_modes": [p.name for p in Mode],
            }
        )
    return jsonify({"mode": None, "available_modes": [p.name for p in Mode]})


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


@app.route("/api/hype", methods=["POST"])
def deploy_hype():
    """Deploy hype."""
    global last_hype_time

    if not state_instance or not director_instance:
        return jsonify({"error": "State or Director not initialized"}), 500

    # Deploy hype
    director_instance.deploy_hype()
    last_hype_time = time.time()

    return jsonify(
        {"success": True, "message": "Hype deployed! 🚀", "duration": HYPE_DURATION}
    )


@app.route("/api/hype/status", methods=["GET"])
def get_hype_status():
    """Get the current hype status."""
    global last_hype_time
    current_time = time.time()
    elapsed = current_time - last_hype_time

    if elapsed < HYPE_DURATION:
        # Hype is still active
        remaining = HYPE_DURATION - elapsed
        return jsonify({"active": True, "remaining": remaining})
    else:
        # Hype is no longer active
        return jsonify({"active": False, "remaining": 0})


@app.route("/api/manual_dimmer", methods=["GET"])
def get_manual_dimmer():
    """Get the current manual dimmer value."""
    if state_instance:
        venue = state_instance.venue
        has_dimmer = has_manual_dimmer(venue)
        return jsonify({"value": state_instance.manual_dimmer, "supported": has_dimmer})
    return jsonify({"value": 0, "supported": False})


@app.route("/api/manual_dimmer", methods=["POST"])
def set_manual_dimmer():
    """Set the manual dimmer value."""
    if state_instance:
        data = request.json
        if "value" in data:
            value = float(data["value"])
            # Ensure value is between 0 and 1
            value = max(0, min(1, value))
            state_instance.set_manual_dimmer(value)
            return jsonify({"success": True, "value": value})
    return jsonify({"success": False, "error": "Invalid request"})


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


def start_web_server(state, director=None, host="0.0.0.0", port=5000, threaded=True):
    """Start the web server in a separate thread or return the app for main thread integration."""
    global state_instance, director_instance
    state_instance = state
    director_instance = director

    # Suppress Flask/Werkzeug logs
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.logger.setLevel(logging.ERROR)

    # Get local IP address
    local_ip = get_local_ip()
    print(f"\n🌐 Web interface available at: http://{local_ip}:{port}/")
    print(f"📱 Connect from your mobile device using the above URL\n")

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
