// Main menu JavaScript

// Update time display
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true 
    });
    const timeElement = document.getElementById('time');
    if (timeElement) {
        timeElement.textContent = timeString;
    }
}

// Track last navigation URL to avoid redirect loops
let lastNavigationUrl = null;

// Check for navigation URL from iPhone
async function checkNavigationUrl() {
    try {
        const response = await fetch('/api/navigation/current');
        const data = await response.json();
        
        if (data.ok && data.maps_url) {
            // Only redirect if this is a new URL (different from last one)
            if (data.maps_url !== lastNavigationUrl) {
                lastNavigationUrl = data.maps_url;
                console.log('Navigation URL detected, redirecting to:', data.maps_url);
                // Redirect to the navigation view page
                window.location.href = '/navigation';
            }
        }
    } catch (error) {
        // Silently fail - navigation check is optional
        console.debug('Navigation URL check failed:', error);
    }
}

// Update status from API
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        // Update status indicator
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) {
            if (data.music_playing) {
                statusIndicator.textContent = 'PLAYING';
                statusIndicator.style.color = '#4CAF50';
            } else if (data.bluetooth_connected) {
                statusIndicator.textContent = 'CONNECTED';
                statusIndicator.style.color = '#2196F3';
            } else {
                statusIndicator.textContent = 'READY';
                statusIndicator.style.color = '#666';
            }
        }
        
        // Update sensor info
        if (data.sense_hat_data) {
            const tempElement = document.getElementById('temperature');
            const humidityElement = document.getElementById('humidity');
            
            if (tempElement && data.sense_hat_data.temperature) {
                tempElement.textContent = `${data.sense_hat_data.temperature}°C`;
            }
            if (humidityElement && data.sense_hat_data.humidity) {
                humidityElement.textContent = `${data.sense_hat_data.humidity}%`;
            }
        }
    } catch (error) {
        console.error('Error updating status:', error);
    }
}

// Check if emoji are supported and render properly
function checkEmojiSupport() {
    const testEmoji = document.createElement('canvas');
    const ctx = testEmoji.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '32px Arial';
    ctx.fillText('🎵', 0, 0);
    
    // If canvas shows nothing or garbled text, emoji might not be supported
    // In that case, we'll rely on the browser's native rendering
    // The CSS already has fallback font families
}

// Voice control state
let voiceActive = false;

// Start voice control
function startVoice() {
    fetch('/api/voice/start', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            if (data.status === 'voice_started') {
                voiceActive = true;
                const btn = document.getElementById('voiceBtn');
                if (btn) {
                    btn.textContent = 'LISTENING...';
                    btn.classList.add('active');
                }
                console.log('Voice control activated');
            }
        })
        .catch(err => {
            console.error('Error starting voice control:', err);
        });
}

// Stop voice control
function stopVoice() {
    fetch('/api/voice/stop', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            if (data.status === 'voice_stopped') {
                voiceActive = false;
                const btn = document.getElementById('voiceBtn');
                if (btn) {
                    btn.textContent = 'VOICE';
                    btn.classList.remove('active');
                }
                console.log('Voice control stopped');
            }
        })
        .catch(err => {
            console.error('Error stopping voice control:', err);
        });
}

// Toggle voice control on/off
function toggleVoice() {
    if (voiceActive) {
        stopVoice();
    } else {
        startVoice();
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updateTime();
    updateStatus();
    checkNavigationUrl();
    checkEmojiSupport();
    
    // Update time every second
    setInterval(updateTime, 1000);
    
    // Update status every 5 seconds
    setInterval(updateStatus, 5000);
    
    // Check for navigation URL every 2 seconds (more frequent for responsiveness)
    setInterval(checkNavigationUrl, 2000);
});

