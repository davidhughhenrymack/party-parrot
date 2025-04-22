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
});