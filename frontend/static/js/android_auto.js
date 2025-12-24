// Android Auto JavaScript

let isActive = false;

const startBtn = document.getElementById('start-auto-btn');
const stopBtn = document.getElementById('stop-auto-btn');
const statusIcon = document.getElementById('auto-status-icon');
const statusText = document.getElementById('auto-status-text');
const statusDesc = document.getElementById('auto-status-desc');

if (startBtn) {
    startBtn.addEventListener('click', async () => {
        await startAndroidAuto();
    });
}

if (stopBtn) {
    stopBtn.addEventListener('click', async () => {
        await stopAndroidAuto();
    });
}

async function startAndroidAuto() {
    try {
        const response = await fetch('/api/android_auto/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success) {
            isActive = true;
            updateUI();
        } else {
            alert('Failed to start Android Auto: ' + data.message);
        }
    } catch (error) {
        console.error('Error starting Android Auto:', error);
        alert('Error starting Android Auto');
    }
}

async function stopAndroidAuto() {
    try {
        const response = await fetch('/api/android_auto/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success) {
            isActive = false;
            updateUI();
        }
    } catch (error) {
        console.error('Error stopping Android Auto:', error);
    }
}

function updateUI() {
    if (isActive) {
        statusIcon.textContent = 'ON';
        statusText.textContent = 'Android Auto Active';
        statusDesc.textContent = 'Your Android phone is connected and ready';
        startBtn.style.display = 'none';
        stopBtn.style.display = 'block';
    } else {
        statusIcon.textContent = 'OFF';
        statusText.textContent = 'Android Auto Not Active';
        statusDesc.textContent = 'Connect your Android phone to use Android Auto';
        startBtn.style.display = 'block';
        stopBtn.style.display = 'none';
    }
}

// Check status on load
async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        // You might want to add Android Auto status to the API response
        updateUI();
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

document.addEventListener('DOMContentLoaded', checkStatus);

