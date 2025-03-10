document.addEventListener('DOMContentLoaded', function() {
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
            
            // Reset button text
            button.textContent = btnPhrase.charAt(0).toUpperCase() + btnPhrase.slice(1);
            button.disabled = false;
            button.classList.remove('loading');
            
            // Set active state
            if (btnPhrase === phrase) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });
    }
    
    // Function to fetch current phrase
    function fetchCurrentPhrase() {
        fetch('/api/phrase')
            .then(response => response.json())
            .then(data => {
                if (data.phrase) {
                    updateUIForPhrase(data.phrase);
                } else {
                    document.getElementById('current-phrase').textContent = 'None';
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
            if (!data.success) {
                console.error('Error setting phrase:', data.error);
                alert('Error setting phrase: ' + data.error);
                
                // Refresh to get the actual current state
                fetchCurrentPhrase();
            }
        })
        .catch(error => {
            console.error('Error setting phrase:', error);
            alert('Error setting phrase');
            
            // Refresh to get the actual current state
            fetchCurrentPhrase();
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
});