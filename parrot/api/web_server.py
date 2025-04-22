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


def create_static_files():
    """Create the static files directory and the HTML/CSS/JS files."""
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(current_dir, "static")
    os.makedirs(static_dir, exist_ok=True)

    # Create index.html
    with open(os.path.join(static_dir, "index.html"), "w") as f:
        f.write(
            """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Party Parrot</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="parrot-background"></div>
    <div class="container">
        <div class="current-mode">
            <h2>Current mode: <span id="current-mode">Loading...</span></h2>
        </div>
        <div class="mode-buttons">
            <button class="mode-button" data-mode="party">Party</button>
            <button class="mode-button" data-mode="twinkle">Twinkle</button>
            <button class="mode-button" data-mode="blackout">Blackout</button>
        </div>
        <div class="hype-container">
            <button id="deploy-hype" class="hype-button">Deploy Hype 🚀</button>
        </div>
        <div id="manual-dimmer-container" class="manual-dimmer-container" style="display: none;">
            <h3>Manual Dimmer</h3>
            <input type="range" id="manual-dimmer-slider" min="0" max="100" value="0" class="slider">
            <div class="dimmer-value"><span id="dimmer-value">0</span>%</div>
        </div>
    </div>
    <script src="script.js"></script>
</body>
</html>"""
        )

    # Create styles.css
    with open(os.path.join(static_dir, "styles.css"), "w") as f:
        f.write(
            """* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: Arial, sans-serif;
    background-color: #121212;
    color: #ffffff;
    position: relative;
    overflow: hidden;
}

.parrot-background {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -1;
    background-image: url('data:image/gif;base64,R0lGODlhZABkALMPAOxELvFgUPJnWutAKe5PO+1JNOo7JO9WQvBbSvRxZPV4a/eBdfeIffmYjfqgl////yH/C05FVFNDQVBFMi4wAwEAAAAh+QQFCgAPACwAAAAAZABkAAAE//DJSau9OOvNu/9gKI5kaZ5oqq5s675wLM90bd94ru987//AoHBILBqPyKRyyWw6n9CodEqtWq/YrHbL7Xq/4LB4TC6bz+i0es1uu9/wuHxOr9vv+Lx+z+/7/4CBgoOEhYaHiImKi4yNjo+QkZKTlJWWl5iZmpucnZ6foKGio6SlpqeoqaqrrK2ur7CxsrO0tba3uLm6u7y9vr/AwcLDxMXGx8jJysvMzc7P0NHS09TV1tfY2drb3N3e3+Dh4uPk5ebn6Onq6+zt7u/w8fLz9PX29/j5+vv8/f7/AAMKHEiwoMGDCBMqXMiwocOHECNKnEixosWLGDNq3Mixo8ePIEOKHEmypMmTKFOqXMmypcuXMGPKnEmzps2bOHPq3Mmzp8+fQIMKHUq0qNGjSJMqXcq0qdOnUKNKnUq1qtWrWLNq3cq1q9evYMOKHUu2rNmzaNOqXcu2rdu3cOPKnUu3rt27ePPq3cu3r9+/gAMLHky4sOHDiBMrXsy4sePHkCNLnky5suXLmDNr3sy5s+fPoEOLHk26tOnTqFOrXs26tevXsGPLnk27tu3buHPr3s27t+/fwIMLH068uPHjyJMrX868ufPn0KNLn069uvXr2LNr3869u/fv4MOLH0++vPnz6NOrX8++vfv38OPLn0+/vv37+PPr38+/v///AAYo4IAEFmjggQgmqOCCDDbo4IMQRijhhBRWaOGFGGao4YYcdujhhyCGKOKIJJZo4okopqjiiiy26OKLMMYo44w01mjjjTjmqOOOPPbo449ABinkkEQWaeSRSCap5JJMNunkk1BGKeWUVFZp5ZVYZqnlllx26eWXYIYp5phklmnmmWimqeaabLbp5ptwxinnnHTWaeedeOap55589unnn4AGKuighBZq6KGIJqrooow26uijkEYq6aSUVmrppZhmqummnHbq6aeghirqqKSWauqpqKaq6qqsturqq7DGKuustNZq66245qrrrrz26uuvwAYr7LDEFmvsscgmq+yyzDbr7LPQRivttNRWa+212Gar7bbcduvtt+CGK+645JZr7rnopqvuuuy26+678MYr77z01mvvvfjmq+++/Pbr778AByzwwAQXbPDBCCes8MIMN+zwwxBHLPHEFFds8cUYZ6zxxhx37PHHIIcs8sgkl2zyySinrPLKLLfs8sswxyzzzDTXbPPNOOes88489+zzz0AHLfTQRBdt9NFIJ6300kw37fTTUEct9dRUV2311VhnrfXWXHft9ddghy322GSXbfbZaKet9tpst+3223DHLffcdNdt99145633//3467/v7TfggAs+OOGFG3444oknbvjijDf+d+GQRy755JRXbvnlmGeu+eacd+7556CHLvropJdu+umop6766qy37vrrsMcu++y012777bjnrvvuvPfu++/ABy/88MQXb/zxyCev/PLMN+/889BHL/301Fdv/fXYZ6/99tx37/334Icv/vjkl2/++einr/767Lfv/vvwxy///PTXb//9+Oev//789+///wAMoAAHSMACGvCACEygAhfIwAY68IEQjKAEJ0jBClrwghjMoAY3yMEOevCDIAyhCEdIwhKa8IQoTKEKV8jCFrrwhTCMoQxnSMMa2vCGOMyhDnfIwx768IdADKIQh0jEIhrxiEhMohKXyMQmOvGJUIyiFKdIxSpa8YpYzKIWt8jFLnrxi2AMoxjHSMYymvGMaEyjGtfIxja68Y1wjKMc50jHOtrxjnjMox73yMc++vGPgAykIAdJyEIa8pCITKQiF8nIRjrykZCMpCQnSclKWvKSmMykJjfJyU568pOgDKUoR0nKUprylKhMpSpXycpWuvKVsIylLGdJy1ra8pa4zKUud8nLXvryl8AMpjCHScxiGvOYyEymMpfJzGY685nQjKY0p0nNalrzmtjMpja3yc1uevOb4AynOMdJznKa85zoTKc618nOdrrznfCMpzznSc962vOe+MynPvfJz376858ADahAB0rQghr0oAhNqEIXytCGOvShEI2oRCdK0Ypa9KIYzahGN8rRjnr0oyANqUhHStKSmvSkKE2pSlfK0pa69KUwjalMZ0rTmtr0pjjNqU53ytOe+vSnQA2qUIdK1KIa9ahITapSl8rUpjr1qVCNqlSnStWqWvWqWM2qVrfK1a569atgDatYx0rWspr1rGhNq1rXyta2uvWtcI2rXOdK17ra9a54zate98rXvvr1r4ANrGAHS9jCGvawiE2sYhfL2MY69rGQjaxkJ0vZylr2spjNrGY3y9nOevazoA2taEdL2tKa9rSoTa1qV8va1rr2tbCNrWxnS9va2va2uM2tbnfL29769rfADa5wh0vc4hr3uMhNrnKXy9zmOve50I2udKdL3epa97rYza52t8vd7nr3u+ANr3jHS97ymve86E2vetfL3va6973wja9850vf+tr3vvjNr373y9/++ve/AA6wgAdM4AIb+MAITrCCF8zgBjv4wRCOsIQnTOEKW/jCGM6whjfM4Q57+MMgDrGIR0ziEpv4xChOsYpXzOIWu/jFMI6xjGdM4xrb+MY4zrGOd8zjHvv4x0AOspCHTOQiG/nISE6ykpfM5CY7+clQjrKUp0zlKlv5yljOspa3zOUue/nLYA6zmMdM5jKb+cxoTrOa18zmNrv5zXCOs5znTOc62/nOeM6znvfM5z77+c+ADrSgB03oQhv60IhOtKIXzehGO/rRkI60pCdN6Upb+tKYzrSmN83pTnv606AOtahHTepSm/rUqE61qlfN6la7+tWwjrWsZ03rWtv61rjOta53zete+/rXwA62sIdN7GIb+9jITrayf21rZjv72dCOtrSnTe1qW/va2M62trfN7W57+9vgDre4x03ucpv73OhOt7rXze52u/vd8I63vOdN73rb+974zre+983vfvv73wAPuMAHTvCCG/zgCE+4whfO8IY7/OEQj7jEJ07xilv84hjPuMY3zvGOe/zjIA+5yEdO8pKb/OQoT7nKV87ylrv85TCPucxnTvOa2/zmOM+5znfO8577/OdAD7rQh070ohv96EhPutKXzvSmO/3pUI+61KdO9apb/epYz7rWt871rnv962APu9jHTvaym/3saE+72tfO9ra7/e1wj7vc5073utv97njPu973zve++/3vgA+84AdP+MIb/vCIT7ziF8/4xjv+8ZCPvOQnT/nKW/7ymM+85jfP+c57/vOgD73oR0/60pv+9KhPvepXz/rWu/71sI+97GdP+9rb/va4z73ud8/73vv+98APvvCHT/ziG//4yE++8pfP/OY7//nQj770p0/96lv/+tjPvva3z/3ue//74A+/+MdP/vKb//zoT7/6189+EQAAOw==');
    opacity: 0.1;
    pointer-events: none;
}

.container {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
}

.current-mode {
    background-color: #1e1e1e;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 30px;
    text-align: center;
    position: relative;
}

.mode-buttons {
    display: grid;
    grid-template-columns: 1fr;
    gap: 15px;
    margin-bottom: 30px;
}

.mode-button {
    background-color: #2196f3;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 20px;
    font-size: 18px;
    cursor: pointer;
    transition: all 0.3s;
    position: relative;
    overflow: hidden;
}

.mode-button:hover {
    background-color: #1976d2;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.mode-button:active {
    background-color: #0d47a1;
    transform: translateY(0);
}

.mode-button.active {
    box-shadow: 0 0 15px rgba(255, 255, 255, 0.5);
    transform: scale(1.05);
}

.mode-button.active::after {
    content: "✓";
    position: absolute;
    top: 10px;
    right: 10px;
    font-size: 14px;
    background-color: rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.mode-button[data-mode="party"] {
    background-color: #f44336;
}

.mode-button[data-mode="party"]:hover {
    background-color: #d32f2f;
}

.mode-button[data-mode="twinkle"] {
    background-color: #9c27b0;
}

.mode-button[data-mode="twinkle"]:hover {
    background-color: #7b1fa2;
}

.mode-button[data-mode="blackout"] {
    background-color: #212121;
}

.mode-button[data-mode="blackout"]:hover {
    background-color: #000000;
}

.hype-container {
    margin-top: 4em;
    text-align: center;
}

.hype-button {
    background: linear-gradient(45deg, #ff9800, #f44336);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 20px 40px;
    font-size: 20px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    position: relative;
    overflow: hidden;
    width: 100%;
    max-width: 400px;
    margin: 0 auto;
}

.hype-button:hover {
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
}

.hype-button:active {
    transform: translateY(0) scale(0.98);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.hype-button.active {
    background-color: #ff3d00;
    animation: pulse 1.5s infinite;
}

.manual-dimmer-container {
    background-color: #1e1e1e;
    padding: 20px;
    border-radius: 8px;
    margin-top: 30px;
    text-align: center;
}

.manual-dimmer-container h3 {
    margin-bottom: 15px;
    color: #ffffff;
}

.slider {
    -webkit-appearance: none;
    width: 100%;
    height: 15px;
    border-radius: 5px;
    background: #333333;
    outline: none;
    margin-bottom: 10px;
}

.slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 25px;
    height: 25px;
    border-radius: 50%;
    background: #ff3d00;
    cursor: pointer;
}

.slider::-moz-range-thumb {
    width: 25px;
    height: 25px;
    border-radius: 50%;
    background: #ff3d00;
    cursor: pointer;
}

.dimmer-value {
    font-size: 18px;
    color: #ffffff;
    margin-top: 5px;
}

@keyframes pulse {
    0% {
        box-shadow: 0 0 0 0 rgba(255, 152, 0, 0.7);
    }
    70% {
        box-shadow: 0 0 0 15px rgba(255, 152, 0, 0);
    }
    100% {
        box-shadow: 0 0 0 0 rgba(255, 152, 0, 0);
    }
}

@media (min-width: 480px) {
    .mode-buttons {
        grid-template-columns: 1fr 1fr;
    }
    
    .mode-button[data-mode="blackout"] {
        grid-column: span 2;
    }
}"""
        )

    # Create script.js
    with open(os.path.join(static_dir, "script.js"), "w") as f:
        f.write(
            """document.addEventListener('DOMContentLoaded', function() {
    // Get current mode on page load
    fetchCurrentmode();
    
    // Add event listeners to mode buttons
    const modeButtons = document.querySelectorAll('.mode-button');
    modeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const mode = this.getAttribute('data-mode');
            
            // Update UI immediately for better responsiveness
            updateUIFormode(mode);
            
            // Then send the request
            setmode(mode);
        });
    });
    
    // Add event listener to hype button
    const hypeButton = document.getElementById('deploy-hype');
    hypeButton.addEventListener('click', function() {
        deployHype();
    });
    
    // Function to update UI for a mode
    function updateUIFormode(mode) {
        const currentmodeElement = document.getElementById('current-mode');
        currentmodeElement.textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
        
        // Update button states
        modeButtons.forEach(button => {
            const btnmode = button.getAttribute('data-mode');
            
            // Set active state
            if (btnmode === mode) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });
    }
    
    // Function to deploy hype
    function deployHype() {
        const hypeButton = document.getElementById('deploy-hype');
        
        // Don't do anything if already active
        if (hypeButton.classList.contains('active')) {
            return;
        }
        
        // Set button to active state
        hypeButton.classList.add('active');
        hypeButton.textContent = 'Deploying Hype 🚀🔥';
        
        // Send request to deploy hype
        fetch('/api/hype', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Hype deployed:', data);
            
            // Start checking hype status
            checkHypeStatus();
        })
        .catch(error => {
            console.error('Error deploying hype:', error);
            
            // Reset button after error
            hypeButton.classList.remove('active');
            hypeButton.textContent = 'Deploy Hype 🚀';
        });
    }
    
    // Function to check hype status
    function checkHypeStatus() {
        const hypeButton = document.getElementById('deploy-hype');
        
        fetch('/api/hype/status')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.active) {
                    // Hype is still active
                    const remainingSeconds = Math.round(data.remaining * 10) / 10;
                    hypeButton.textContent = `Hype Active 🔥 (${remainingSeconds}s)`;
                    
                    // Check again in 500ms
                    setTimeout(checkHypeStatus, 500);
                } else {
                    // Hype is no longer active
                    hypeButton.classList.remove('active');
                    hypeButton.textContent = 'Deploy Hype 🚀';
                }
            })
            .catch(error => {
                console.error('Error checking hype status:', error);
                
                // Reset button after error
                hypeButton.classList.remove('active');
                hypeButton.textContent = 'Deploy Hype 🚀';
            });
    }
    
    // Function to update connection status
    function updateConnectionStatus(isConnected) {
        // Update UI based on connection status
        if (!isConnected) {
            document.getElementById('current-mode').textContent = 'Not Connected';
            
            // Disable hype button when not connected
            const hypeButton = document.getElementById('deploy-hype');
            hypeButton.disabled = true;
            hypeButton.textContent = 'Not Connected';
            hypeButton.style.opacity = '0.5';
        } else {
            // Re-enable hype button when connected
            const hypeButton = document.getElementById('deploy-hype');
            hypeButton.disabled = false;
            if (!hypeButton.classList.contains('active')) {
                hypeButton.textContent = 'Deploy Hype 🚀';
                hypeButton.style.opacity = '1';
            }
        }
    }
    
    // Function to fetch current mode
    function fetchCurrentmode() {
        fetch('/api/mode')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                updateConnectionStatus(true);
                return response.json();
            })
            .then(data => {
                if (data.mode) {
                    updateUIFormode(data.mode);
                } else {
                    document.getElementById('current-mode').textContent = 'None';
                }
                
                // Also check hype status
                checkHypeStatus();
            })
            .catch(error => {
                console.error('Error fetching mode:', error);
                document.getElementById('current-mode').textContent = 'Not Connected';
                updateConnectionStatus(false);
                
                // Reset buttons on error
                modeButtons.forEach(button => {
                    button.classList.remove('active');
                });
            });
    }
    
    // Function to set mode
    function setmode(mode) {
        fetch('/api/mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ mode: mode }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            updateConnectionStatus(true);
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                console.error('Error setting mode:', data.error);
                alert('Error setting mode: ' + data.error);
                
                // Refresh to get the actual current state
                fetchCurrentmode();
            }
        })
        .catch(error => {
            console.error('Error setting mode:', error);
            updateConnectionStatus(false);
            
            // Refresh to get the actual current state
            fetchCurrentmode();
        });
    }
    
    // Initial connection check
    updateConnectionStatus(true);
    
    // Refresh current mode every 5 seconds
    setInterval(fetchCurrentmode, 5000);
    
    // Check connection status every 5 seconds
    setInterval(function() {
        fetch('/api/mode')
            .then(response => {
                updateConnectionStatus(true);
            })
            .catch(error => {
                updateConnectionStatus(false);
            });
    }, 5000);
    
    // Check for manual dimmer support and initialize if available
    checkManualDimmerSupport();
    
    // Periodically check for manual dimmer support in case venue changes
    setInterval(checkManualDimmerSupport, 5000);
    
    // Function to check if the venue supports manual dimmers
    function checkManualDimmerSupport() {
        fetch('/api/manual_dimmer')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                const dimmerContainer = document.getElementById('manual-dimmer-container');
                
                // Only show the manual dimmer if it's supported
                if (data.supported) {
                    // Show the manual dimmer container
                    dimmerContainer.style.display = 'block';
                    
                    // Set the initial value
                    const slider = document.getElementById('manual-dimmer-slider');
                    const valueDisplay = document.getElementById('dimmer-value');
                    
                    // Convert from 0-1 to 0-100
                    const value = Math.round(data.value * 100);
                    slider.value = value;
                    valueDisplay.textContent = value;
                    
                    // Add event listener for slider changes
                    slider.addEventListener('input', function() {
                        // Update the display value
                        valueDisplay.textContent = this.value;
                    });
                    
                    // Add event listener for when slider is released
                    slider.addEventListener('change', function() {
                        // Send the new value to the server
                        setManualDimmer(this.value / 100);
                    });
                } else {
                    // Hide the manual dimmer container if not supported
                    dimmerContainer.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error checking manual dimmer support:', error);
                // Hide the manual dimmer container if there's an error
                const dimmerContainer = document.getElementById('manual-dimmer-container');
                dimmerContainer.style.display = 'none';
            });
    }
    
    // Function to set the manual dimmer value
    function setManualDimmer(value) {
        fetch('/api/manual_dimmer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ value: value })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Manual dimmer set:', data);
        })
        .catch(error => {
            console.error('Error setting manual dimmer:', error);
        });
    }
});"""
        )


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


def start_web_server(state, director=None, host="0.0.0.0", port=5000):
    """Start the web server in a separate thread."""
    global state_instance, director_instance
    state_instance = state
    director_instance = director

    # Create static files
    create_static_files()

    # Get local IP address
    local_ip = get_local_ip()
    print(f"\n🌐 Web interface available at: http://{local_ip}:{port}/")
    print(f"📱 Connect from your mobile device using the above URL\n")

    # Start Flask in a separate thread
    threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
    ).start()
