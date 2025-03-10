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
});