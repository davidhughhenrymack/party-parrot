import os
import socket
import threading
import time
from flask import Flask, jsonify, request, send_from_directory
from parrot.director.mode import Mode
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

        # Try to directly update the GUI if possible
        try:
            import tkinter as tk

            if hasattr(tk, "_default_root") and tk._default_root:
                for window in tk.Tk.winfo_children(tk._default_root):
                    if hasattr(window, "_force_update_button_appearance"):
                        print(
                            f"Web server: Directly updating GUI for mode: {mode.name}"
                        )
                        # Schedule the update to run in the main thread
                        window.after(
                            100, lambda: window._force_update_button_appearance(mode)
                        )
                        break
        except Exception as e:
            print(f"Web server: Could not directly update GUI: {e}")

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


def start_web_server(state, director=None, host="0.0.0.0", port=5000):
    """Start the web server in a separate thread."""
    global state_instance, director_instance
    state_instance = state
    director_instance = director

    # Get local IP address
    local_ip = get_local_ip()
    print(f"\n🌐 Web interface available at: http://{local_ip}:{port}/")
    print(f"📱 Connect from your mobile device using the above URL\n")

    # Start Flask in a separate thread
    threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
    ).start()
