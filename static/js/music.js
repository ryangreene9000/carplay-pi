// Music player JavaScript

let isPlaying = false;
let currentVolume = 50;

// Play/Pause button
const playPauseBtn = document.getElementById('play-pause-btn');
if (playPauseBtn) {
    playPauseBtn.addEventListener('click', async () => {
        if (isPlaying) {
            await pauseMusic();
        } else {
            await playMusic();
        }
    });
}

// Previous/Next buttons
document.getElementById('prev-btn')?.addEventListener('click', () => {
    // Previous track functionality
    console.log('Previous track');
});

document.getElementById('next-btn')?.addEventListener('click', () => {
    // Next track functionality
    console.log('Next track');
});

// Volume slider
const volumeSlider = document.getElementById('volume-slider');
const volumeValue = document.getElementById('volume-value');

if (volumeSlider && volumeValue) {
    volumeSlider.value = currentVolume;
    volumeValue.textContent = `${currentVolume}%`;
    
    volumeSlider.addEventListener('input', async (e) => {
        const volume = parseInt(e.target.value);
        currentVolume = volume;
        volumeValue.textContent = `${volume}%`;
        await setVolume(volume);
    });
}

// Bluetooth scan
const scanBtn = document.getElementById('scan-btn');
if (scanBtn) {
    scanBtn.addEventListener('click', async () => {
        scanBtn.disabled = true;
        scanBtn.textContent = 'Scanning...';
        await scanBluetoothDevices();
        scanBtn.disabled = false;
        scanBtn.textContent = 'Scan for Devices';
    });
}

// API functions
async function playMusic() {
    try {
        const response = await fetch('/api/music/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success) {
            isPlaying = true;
            playPauseBtn.textContent = '⏸';
            updateTrackInfo('Playing...', 'Bluetooth Audio');
        }
    } catch (error) {
        console.error('Error playing music:', error);
    }
}

async function pauseMusic() {
    try {
        const response = await fetch('/api/music/pause', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success) {
            isPlaying = false;
            playPauseBtn.textContent = '▶';
        }
    } catch (error) {
        console.error('Error pausing music:', error);
    }
}

async function setVolume(volume) {
    try {
        const response = await fetch('/api/music/volume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ volume })
        });
        const data = await response.json();
        console.log('Volume set:', data);
    } catch (error) {
        console.error('Error setting volume:', error);
    }
}

async function scanBluetoothDevices() {
    try {
        const response = await fetch('/api/bluetooth/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        displayDevices(data.devices || []);
    } catch (error) {
        console.error('Error scanning devices:', error);
        displayDevices([]);
    }
}

function displayDevices(devices) {
    const deviceList = document.getElementById('device-list');
    if (!deviceList) return;
    
    deviceList.innerHTML = '';
    
    if (devices.length === 0) {
        deviceList.innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">No devices found. Make sure Bluetooth is enabled on nearby devices.</p>';
        return;
    }
    
    // Show device count
    const countInfo = document.createElement('p');
    countInfo.style.cssText = 'color: #667eea; font-weight: 600; margin-bottom: 15px;';
    countInfo.textContent = `Found ${devices.length} device${devices.length !== 1 ? 's' : ''}`;
    deviceList.appendChild(countInfo);
    
    devices.forEach(device => {
        const deviceItem = document.createElement('div');
        deviceItem.className = 'device-item';
        
        // Signal strength indicator (if available)
        let signalIndicator = '';
        if (device.rssi !== null && device.rssi !== undefined) {
            const signalStrength = device.rssi > -50 ? '📶' : device.rssi > -70 ? '📶' : '📶';
            const signalQuality = device.rssi > -50 ? 'Excellent' : device.rssi > -70 ? 'Good' : 'Weak';
            signalIndicator = `<span style="color: #888; font-size: 0.8em;">${signalStrength} ${signalQuality} (${device.rssi} dBm)</span>`;
        }
        
        deviceItem.innerHTML = `
            <div style="flex: 1;">
                <strong>${device.name}</strong><br>
                <small style="color: #888;">${device.address}</small><br>
                ${signalIndicator}
            </div>
            <button onclick="connectDevice('${device.address}')" style="white-space: nowrap;">Connect</button>
        `;
        deviceList.appendChild(deviceItem);
    });
}

async function connectDevice(address) {
    try {
        const response = await fetch('/api/bluetooth/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address })
        });
        const data = await response.json();
        
        if (data.success) {
            alert('Connected successfully!');
            updateTrackInfo('Connected', 'Bluetooth Device');
        } else {
            alert('Connection failed: ' + data.message);
        }
    } catch (error) {
        console.error('Error connecting device:', error);
        alert('Error connecting to device');
    }
}

function updateTrackInfo(title, artist) {
    const titleElement = document.getElementById('track-title');
    const artistElement = document.getElementById('track-artist');
    
    if (titleElement) titleElement.textContent = title;
    if (artistElement) artistElement.textContent = artist;
}

// Make connectDevice available globally
window.connectDevice = connectDevice;

// Load initial status
async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        isPlaying = data.music_playing || false;
        currentVolume = data.volume || 50;
        
        if (playPauseBtn) {
            playPauseBtn.textContent = isPlaying ? '⏸' : '▶';
        }
        
        if (volumeSlider) {
            volumeSlider.value = currentVolume;
        }
        
        if (volumeValue) {
            volumeValue.textContent = `${currentVolume}%`;
        }
        
        if (data.current_track) {
            updateTrackInfo(data.current_track.title, data.current_track.artist);
        }
    } catch (error) {
        console.error('Error loading status:', error);
    }
}

document.addEventListener('DOMContentLoaded', loadStatus);

