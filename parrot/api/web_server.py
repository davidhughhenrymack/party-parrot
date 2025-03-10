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
        # Use the thread-safe method to set the phrase
        state_instance.set_phrase_thread_safe(phrase)
        return jsonify({"success": True, "phrase": phrase.name})
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
    <div class="container">
        <h1>Party Parrot</h1>
        <div class="current-phrase">
            <h2>Current Phrase: <span id="current-phrase">Loading...</span></h2>
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
}

.container {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
}

h1 {
    text-align: center;
    margin-bottom: 30px;
    color: #ff9800;
}

.current-phrase {
    background-color: #1e1e1e;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 30px;
    text-align: center;
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
    transition: background-color 0.3s;
    position: relative;
    overflow: hidden;
}

.phrase-button:hover {
    background-color: #1976d2;
}

.phrase-button:active {
    background-color: #0d47a1;
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
            
            // Show loading state
            this.classList.add('loading');
            this.textContent = `Setting ${phrase}...`;
            
            // Disable all buttons during request
            phraseButtons.forEach(btn => btn.disabled = true);
            
            setPhrase(phrase);
        });
    });
    
    // Function to fetch current phrase
    function fetchCurrentPhrase() {
        fetch('/api/phrase')
            .then(response => response.json())
            .then(data => {
                const currentPhraseElement = document.getElementById('current-phrase');
                if (data.phrase) {
                    currentPhraseElement.textContent = data.phrase.charAt(0).toUpperCase() + data.phrase.slice(1);
                    
                    // Highlight the active button
                    phraseButtons.forEach(button => {
                        if (button.getAttribute('data-phrase') === data.phrase) {
                            button.classList.add('active');
                        } else {
                            button.classList.remove('active');
                        }
                        
                        // Reset button text
                        const phrase = button.getAttribute('data-phrase');
                        button.textContent = phrase.charAt(0).toUpperCase() + phrase.slice(1);
                        button.disabled = false;
                        button.classList.remove('loading');
                    });
                } else {
                    currentPhraseElement.textContent = 'None';
                }
            })
            .catch(error => {
                console.error('Error fetching phrase:', error);
                document.getElementById('current-phrase').textContent = 'Error';
                
                // Reset buttons on error
                phraseButtons.forEach(button => {
                    const phrase = button.getAttribute('data-phrase');
                    button.textContent = phrase.charAt(0).toUpperCase() + phrase.slice(1);
                    button.disabled = false;
                    button.classList.remove('loading');
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
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                fetchCurrentPhrase();
            } else {
                console.error('Error setting phrase:', data.error);
                alert('Error setting phrase: ' + data.error);
                
                // Reset buttons on error
                phraseButtons.forEach(button => {
                    const btnPhrase = button.getAttribute('data-phrase');
                    button.textContent = btnPhrase.charAt(0).toUpperCase() + btnPhrase.slice(1);
                    button.disabled = false;
                    button.classList.remove('loading');
                });
            }
        })
        .catch(error => {
            console.error('Error setting phrase:', error);
            alert('Error setting phrase');
            
            // Reset buttons on error
            phraseButtons.forEach(button => {
                const btnPhrase = button.getAttribute('data-phrase');
                button.textContent = btnPhrase.charAt(0).toUpperCase() + btnPhrase.slice(1);
                button.disabled = false;
                button.classList.remove('loading');
            });
        });
    }
    
    // Add CSS for loading state
    const style = document.createElement('style');
    style.textContent = `
        .phrase-button.loading {
            opacity: 0.7;
            cursor: wait;
        }
    `;
    document.head.appendChild(style);
    
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
