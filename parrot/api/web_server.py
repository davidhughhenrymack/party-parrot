import os
import socket
import threading
from flask import Flask, jsonify, request, send_from_directory
from parrot.director.phrase import Phrase
from parrot.state import State

# Create Flask app
app = Flask(__name__)

# Global reference to the state object
state_instance = None


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


@app.route("/api/phrase", methods=["GET"])
def get_phrase():
    """Get the current phrase."""
    if state_instance and state_instance.phrase:
        return jsonify(
            {
                "phrase": state_instance.phrase.name,
                "available_phrases": [p.name for p in Phrase],
            }
        )
    return jsonify({"phrase": None, "available_phrases": [p.name for p in Phrase]})


@app.route("/api/phrase", methods=["POST"])
def set_phrase():
    """Set the current phrase."""
    if not state_instance:
        return jsonify({"error": "State not initialized"}), 500

    data = request.json
    if not data or "phrase" not in data:
        return jsonify({"error": "Missing phrase parameter"}), 400

    phrase_name = data["phrase"]
    try:
        phrase = Phrase[phrase_name]

        # Return success immediately to make the web UI responsive
        response = jsonify({"success": True, "phrase": phrase.name})

        # Use the thread-safe method to set the phrase (after preparing the response)
        state_instance.set_phrase_thread_safe(phrase)

        # Try to directly update the GUI if possible
        try:
            import tkinter as tk

            if hasattr(tk, "_default_root") and tk._default_root:
                for window in tk.Tk.winfo_children(tk._default_root):
                    if hasattr(window, "_force_update_button_appearance"):
                        print(
                            f"Web server: Directly updating GUI for phrase: {phrase.name}"
                        )
                        # Schedule the update to run in the main thread
                        window.after(
                            100, lambda: window._force_update_button_appearance(phrase)
                        )
                        break
        except Exception as e:
            print(f"Web server: Could not directly update GUI: {e}")

        return response
    except KeyError:
        return (
            jsonify(
                {
                    "error": f"Invalid phrase: {phrase_name}. Available phrases: {[p.name for p in Phrase]}"
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
        <div class="current-phrase">
            <h2>Current Phrase: <span id="current-phrase">Loading...</span></h2>
            <div id="connection-status" class="connection-status">Checking connection...</div>
        </div>
        <div class="phrase-buttons">
            <button class="phrase-button" data-phrase="party">Party</button>
            <button class="phrase-button" data-phrase="twinkle">Twinkle</button>
            <button class="phrase-button" data-phrase="blackout">Blackout</button>
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

.current-phrase {
    background-color: #1e1e1e;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 30px;
    text-align: center;
    position: relative;
}

.connection-status {
    font-size: 12px;
    margin-top: 10px;
    color: #aaa;
}

.connection-status.connected {
    color: #4CAF50;
}

.connection-status.disconnected {
    color: #F44336;
}

.phrase-buttons {
    display: grid;
    grid-template-columns: 1fr;
    gap: 15px;
}

.phrase-button {
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

.phrase-button:hover {
    background-color: #1976d2;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.phrase-button:active {
    background-color: #0d47a1;
    transform: translateY(0);
}

.phrase-button.active {
    box-shadow: 0 0 15px rgba(255, 255, 255, 0.5);
    transform: scale(1.05);
}

.phrase-button.active::after {
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

.phrase-button[data-phrase="party"] {
    background-color: #f44336;
}

.phrase-button[data-phrase="party"]:hover {
    background-color: #d32f2f;
}

.phrase-button[data-phrase="twinkle"] {
    background-color: #9c27b0;
}

.phrase-button[data-phrase="twinkle"]:hover {
    background-color: #7b1fa2;
}

.phrase-button[data-phrase="blackout"] {
    background-color: #212121;
}

.phrase-button[data-phrase="blackout"]:hover {
    background-color: #000000;
}

@media (min-width: 480px) {
    .phrase-buttons {
        grid-template-columns: 1fr 1fr;
    }
    
    .phrase-button[data-phrase="blackout"] {
        grid-column: span 2;
    }
}"""
        )

    # Create script.js
    with open(os.path.join(static_dir, "script.js"), "w") as f:
        f.write(
            """document.addEventListener('DOMContentLoaded', function() {
    // Get current phrase on page load
    fetchCurrentPhrase();
    
    // Add event listeners to phrase buttons
    const phraseButtons = document.querySelectorAll('.phrase-button');
    phraseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const phrase = this.getAttribute('data-phrase');
            
            // Update UI immediately for better responsiveness
            updateUIForPhrase(phrase);
            
            // Then send the request
            setPhrase(phrase);
        });
    });
    
    // Function to update UI for a phrase
    function updateUIForPhrase(phrase) {
        const currentPhraseElement = document.getElementById('current-phrase');
        currentPhraseElement.textContent = phrase.charAt(0).toUpperCase() + phrase.slice(1);
        
        // Update button states
        phraseButtons.forEach(button => {
            const btnPhrase = button.getAttribute('data-phrase');
            
            // Set active state
            if (btnPhrase === phrase) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });
    }
    
    // Function to update connection status
    function updateConnectionStatus(isConnected) {
        const statusElement = document.getElementById('connection-status');
        
        if (isConnected) {
            statusElement.textContent = 'Connected to Party Parrot';
            statusElement.className = 'connection-status connected';
        } else {
            statusElement.textContent = 'Not connected to Party Parrot - check if the app is running';
            statusElement.className = 'connection-status disconnected';
        }
    }
    
    // Function to fetch current phrase
    function fetchCurrentPhrase() {
        fetch('/api/phrase')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                updateConnectionStatus(true);
                return response.json();
            })
            .then(data => {
                if (data.phrase) {
                    updateUIForPhrase(data.phrase);
                } else {
                    document.getElementById('current-phrase').textContent = 'None';
                }
            })
            .catch(error => {
                console.error('Error fetching phrase:', error);
                document.getElementById('current-phrase').textContent = 'Not Connected';
                updateConnectionStatus(false);
                
                // Reset buttons on error
                phraseButtons.forEach(button => {
                    button.classList.remove('active');
                });
            });
    }
    
    // Function to set phrase
    function setPhrase(phrase) {
        fetch('/api/phrase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ phrase: phrase }),
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
                console.error('Error setting phrase:', data.error);
                alert('Error setting phrase: ' + data.error);
                
                // Refresh to get the actual current state
                fetchCurrentPhrase();
            }
        })
        .catch(error => {
            console.error('Error setting phrase:', error);
            updateConnectionStatus(false);
            
            // Refresh to get the actual current state
            fetchCurrentPhrase();
        });
    }
    
    // Refresh current phrase every 5 seconds
    setInterval(fetchCurrentPhrase, 5000);
});"""
        )


def start_web_server(state, host="0.0.0.0", port=5000):
    """Start the web server in a separate thread."""
    global state_instance
    state_instance = state

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
