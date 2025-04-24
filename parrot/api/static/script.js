document.addEventListener('DOMContentLoaded', function() {
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
    
    // Add event listener to effect buttons
    const effectButtons = document.querySelectorAll('.effect-button');
    effectButtons.forEach(button => {
        button.addEventListener('click', function() {
            const effect = this.getAttribute('data-effect');
            
            // Update UI immediately for better responsiveness
            updateUIForEffect(effect);
            
            // Then send the request
            setEffect(effect);
        });
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
    
    // Function to update UI for an effect
    function updateUIForEffect(effect) {
        const currentmodeElement = document.getElementById('current-mode');
        currentmodeElement.textContent = effect.charAt(0).toUpperCase() + effect.slice(1);
        
        // Update button states
        effectButtons.forEach(button => {
            const btnEffect = button.getAttribute('data-effect');
            
            // Set active state
            if (btnEffect === effect) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });
    }
    
    // Function to deploy mode
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
            
            // Refresh to get the actual current state
            fetchCurrentmode();
        });
    }
    
    // Function to deploy effect
    function setEffect(effect) {
        fetch('/api/effect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ effect: effect }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                console.error('Error setting effect:', data.error);
                alert('Error setting effect: ' + data.error);
                
                // Refresh to get the actual current state
                fetchCurrentmode();
            }
        })
        .catch(error => {
            console.error('Error setting effect:', error);
            
            // Refresh to get the actual current state
            fetchCurrentmode();
        });
    }
    
    // Function to fetch current mode
    function fetchCurrentmode() {
        fetch('/api/mode')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.mode) {
                    updateUIFormode(data.mode);
                } else {
                    document.getElementById('current-mode').textContent = 'None';
                }
            })
            .catch(error => {
                console.error('Error fetching mode:', error);
                document.getElementById('current-mode').textContent = 'Not Connected';
            });
    }
    
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
});