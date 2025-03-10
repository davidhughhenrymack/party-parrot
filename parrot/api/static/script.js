document.addEventListener('DOMContentLoaded', function() {
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
    
    // Add event listener to hype button
    const hypeButton = document.getElementById('deploy-hype');
    hypeButton.addEventListener('click', function() {
        deployHype();
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
            document.getElementById('current-phrase').textContent = 'Not Connected';
            
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
                
                // Also check hype status
                checkHypeStatus();
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
});