// Music player JavaScript
// Handles Bluetooth connection, media controls, and status updates

let isPlaying = false;
let currentVolume = 50;
let connectedDeviceAddress = null;
let connectedDeviceName = null;
let statusPollInterval = null;

// =============================================================================
// Media Control Buttons
// =============================================================================

// Play/Pause button - uses playerctl toggle
const playPauseBtn = document.getElementById('play-pause-btn');
if (playPauseBtn) {
    playPauseBtn.addEventListener('click', async () => {
        await togglePlayback();
    });
}

// Previous button
document.getElementById('prev-btn')?.addEventListener('click', async () => {
    await previousTrack();
});

// Next button
document.getElementById('next-btn')?.addEventListener('click', async () => {
    await nextTrack();
});

// =============================================================================
// Volume Control
// =============================================================================

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

// =============================================================================
// Bluetooth Scan
// =============================================================================

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

// =============================================================================
// API Functions - Media Controls (using playerctl)
// =============================================================================

async function togglePlayback() {
    try {
        playPauseBtn.disabled = true;
        const response = await fetch('/api/media/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.ok) {
            // Refresh status to get accurate state
            await fetchMediaStatus();
        } else {
            console.warn('Toggle playback:', data.message || data.output);
            showNotification(data.message || data.output || 'No media player available', 'warning');
        }
    } catch (error) {
        console.error('Error toggling playback:', error);
        showNotification('Error controlling playback', 'error');
    } finally {
        playPauseBtn.disabled = false;
    }
}

async function previousTrack() {
    try {
        const response = await fetch('/api/media/previous', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.ok) {
            showNotification('Previous track', 'success');
            // Refresh status after a short delay
            setTimeout(fetchMediaStatus, 500);
        } else {
            showNotification(data.message || data.output || 'Cannot go to previous track', 'warning');
        }
    } catch (error) {
        console.error('Error going to previous track:', error);
    }
}

async function nextTrack() {
    try {
        const response = await fetch('/api/media/next', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.ok) {
            showNotification('Next track', 'success');
            // Refresh status after a short delay
            setTimeout(fetchMediaStatus, 500);
        } else {
            showNotification(data.message || data.output || 'Cannot skip track', 'warning');
        }
    } catch (error) {
        console.error('Error going to next track:', error);
    }
}

async function fetchMediaStatus() {
    try {
        const response = await fetch('/api/media/status');
        const data = await response.json();
        
        // Determine if we have an active media player
        const hasActivePlayer = data && data.ok && data.status !== 'no-player';
        
        if (hasActivePlayer) {
            isPlaying = data.is_playing;
            
            // Update play/pause button icon
            if (playPauseBtn) {
                playPauseBtn.textContent = isPlaying ? '⏸' : '▶';
            }
            
            // Update track info
            if (data.title || data.artist) {
                updateTrackInfo(
                    data.title || 'Unknown Track',
                    data.artist || 'Unknown Artist'
                );
            } else if (data.status === 'Playing' || data.status === 'Paused') {
                updateTrackInfo(data.status, connectedDeviceName || 'Bluetooth Audio');
            }
            
            // Update connection indicator to show connected (media player is active)
            updateConnectionStatus(true, data.source === 'bluez' ? 'Bluetooth Audio' : 'Media Player');
            
        } else {
            // No media player available
            if (playPauseBtn) {
                playPauseBtn.textContent = '▶';
            }
            
            // Update connection indicator to show not connected
            updateConnectionStatus(false);
        }
    } catch (error) {
        console.error('Error fetching media status:', error);
        updateConnectionStatus(false);
    }
}

// =============================================================================
// API Functions - Volume (local system)
// =============================================================================

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

// =============================================================================
// Bluetooth Device Scanning & Display
// =============================================================================

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
        deviceItem.id = `device-${device.address.replace(/:/g, '-')}`;
        
        // Signal strength indicator (if available)
        let signalIndicator = '';
        if (device.rssi !== null && device.rssi !== undefined) {
            const signalQuality = device.rssi > -50 ? 'Excellent' : device.rssi > -70 ? 'Good' : 'Weak';
            const signalColor = device.rssi > -50 ? '#4CAF50' : device.rssi > -70 ? '#FFC107' : '#f44336';
            signalIndicator = `<span style="color: ${signalColor}; font-size: 0.8em;">📶 ${signalQuality} (${device.rssi} dBm)</span>`;
        }
        
        // Check if this device is currently connected
        const isConnected = connectedDeviceAddress === device.address;
        const buttonText = isConnected ? 'Disconnect' : 'Connect';
        const buttonClass = isConnected ? 'btn-disconnect' : 'btn-connect';
        
        deviceItem.innerHTML = `
            <div style="flex: 1;">
                <strong>${device.name}</strong><br>
                <small style="color: #888;">${device.address}</small><br>
                ${signalIndicator}
            </div>
            <button 
                id="btn-${device.address.replace(/:/g, '-')}"
                class="${buttonClass}"
                onclick="${isConnected ? `disconnectDevice('${device.address}')` : `connectDevice('${device.address}', '${device.name}')`}"
                style="white-space: nowrap;">
                ${buttonText}
            </button>
        `;
        deviceList.appendChild(deviceItem);
    });
}

// =============================================================================
// Bluetooth Connect/Disconnect
// =============================================================================

async function connectDevice(address, name) {
    const btnId = `btn-${address.replace(/:/g, '-')}`;
    const btn = document.getElementById(btnId);
    
    try {
        // Update button state
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Connecting...';
        }
        
        showNotification(`Connecting to ${name}...`, 'info');
        
        const response = await fetch('/api/bluetooth/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address })
        });
        const data = await response.json();
        
        if (data.success) {
            connectedDeviceAddress = address;
            connectedDeviceName = name;
            
            showNotification(`Connected to ${name}!`, 'success');
            updateTrackInfo('Connected', name);
            updateConnectionStatus(true, name);
            
            // Update button to show Disconnect
            if (btn) {
                btn.textContent = 'Disconnect';
                btn.className = 'btn-disconnect';
                btn.onclick = () => disconnectDevice(address);
            }
            
            // Start polling media status
            startMediaStatusPolling();
            
        } else {
            showNotification(data.message || 'Connection failed', 'error');
            
            // Show raw output if available for debugging
            if (data.raw_output) {
                console.log('Connection raw output:', data.raw_output);
            }
            
            // Reset button
            if (btn) {
                btn.textContent = 'Connect';
                btn.className = 'btn-connect';
            }
        }
    } catch (error) {
        console.error('Error connecting device:', error);
        showNotification('Error connecting to device', 'error');
        
        if (btn) {
            btn.textContent = 'Connect';
            btn.className = 'btn-connect';
        }
    } finally {
        if (btn) {
            btn.disabled = false;
        }
    }
}

async function disconnectDevice(address) {
    const btnId = `btn-${address.replace(/:/g, '-')}`;
    const btn = document.getElementById(btnId);
    
    try {
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Disconnecting...';
        }
        
        const response = await fetch('/api/bluetooth/disconnect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address })
        });
        const data = await response.json();
        
        if (data.success) {
            connectedDeviceAddress = null;
            connectedDeviceName = null;
            
            showNotification('Disconnected', 'success');
            updateTrackInfo('No track playing', 'Connect a device to play music');
            updateConnectionStatus(false);
            
            // Stop polling
            stopMediaStatusPolling();
            
            // Update button
            if (btn) {
                btn.textContent = 'Connect';
                btn.className = 'btn-connect';
                btn.onclick = () => connectDevice(address, 'Device');
            }
        } else {
            showNotification(data.message || 'Disconnect failed', 'error');
        }
    } catch (error) {
        console.error('Error disconnecting device:', error);
        showNotification('Error disconnecting', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
        }
    }
}

// Make functions available globally
window.connectDevice = connectDevice;
window.disconnectDevice = disconnectDevice;

// =============================================================================
// Media Status Polling
// =============================================================================

function startMediaStatusPolling() {
    // Poll every 2 seconds
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }
    statusPollInterval = setInterval(fetchMediaStatus, 2000);
    
    // Fetch immediately
    fetchMediaStatus();
}

function stopMediaStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
        statusPollInterval = null;
    }
}

// =============================================================================
// UI Helpers
// =============================================================================

function updateTrackInfo(title, artist) {
    const titleElement = document.getElementById('track-title');
    const artistElement = document.getElementById('track-artist');
    
    if (titleElement) titleElement.textContent = title || 'No track playing';
    if (artistElement) artistElement.textContent = artist || 'Connect a device to play music';
}

function updateConnectionStatus(connected, deviceName = null) {
    const indicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    
    if (indicator) {
        indicator.style.background = connected ? '#4CAF50' : '#888';
    }
    
    if (statusText) {
        if (connected && deviceName) {
            statusText.textContent = `Connected to ${deviceName}`;
            statusText.style.color = '#4CAF50';
        } else if (connected) {
            statusText.textContent = 'Connected';
            statusText.style.color = '#4CAF50';
        } else {
            statusText.textContent = 'Not connected';
            statusText.style.color = '#888';
        }
    }
}

function showNotification(message, type = 'info') {
    // Check if there's an existing notification container
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            max-width: 300px;
        `;
        document.body.appendChild(container);
    }
    
    const notification = document.createElement('div');
    
    const colors = {
        success: '#4CAF50',
        error: '#f44336',
        warning: '#FFC107',
        info: '#2196F3'
    };
    
    notification.style.cssText = `
        background: ${colors[type] || colors.info};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease;
        font-weight: 500;
    `;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    .btn-connect {
        background: #667eea;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
    }
    .btn-connect:hover {
        background: #5a6fd6;
    }
    .btn-disconnect {
        background: #f44336;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
    }
    .btn-disconnect:hover {
        background: #d32f2f;
    }
    button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
`;
document.head.appendChild(style);

// =============================================================================
// Initial Load
// =============================================================================

async function loadStatus() {
    try {
        // Check Bluetooth connection status
        const btResponse = await fetch('/api/bluetooth/status');
        const btData = await btResponse.json();
        
        if (btData.connected && btData.connected_device) {
            connectedDeviceAddress = btData.connected_device;
        }
        
        // Load volume status
        const response = await fetch('/api/status');
        const data = await response.json();
        
        currentVolume = data.volume || 50;
        
        if (volumeSlider) {
            volumeSlider.value = currentVolume;
        }
        
        if (volumeValue) {
            volumeValue.textContent = `${currentVolume}%`;
        }
        
        if (data.current_track) {
            updateTrackInfo(data.current_track.title, data.current_track.artist);
        }
        
        // Always start polling media status on page load
        // This will update the connection indicator based on active media player
        startMediaStatusPolling();
        
    } catch (error) {
        console.error('Error loading status:', error);
        // Still try to poll media status even if initial load fails
        startMediaStatusPolling();
    }
}

document.addEventListener('DOMContentLoaded', loadStatus);
