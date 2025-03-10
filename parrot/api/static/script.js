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
});