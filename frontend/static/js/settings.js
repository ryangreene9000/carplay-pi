// Settings JavaScript

// Volume slider
const defaultVolumeSlider = document.getElementById('default-volume');
const defaultVolumeValue = document.getElementById('default-volume-value');

if (defaultVolumeSlider && defaultVolumeValue) {
    defaultVolumeSlider.addEventListener('input', (e) => {
        defaultVolumeValue.textContent = `${e.target.value}%`;
    });
}

// Brightness slider
const brightnessSlider = document.getElementById('brightness');
const brightnessValue = document.getElementById('brightness-value');

if (brightnessSlider && brightnessValue) {
    brightnessSlider.addEventListener('input', (e) => {
        brightnessValue.textContent = `${e.target.value}%`;
    });
}

// Save settings
const saveBtn = document.getElementById('save-settings-btn');
if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
        const settings = {
            defaultVolume: defaultVolumeSlider?.value || 50,
            audioOutput: document.getElementById('audio-output')?.value || 'bluetooth',
            brightness: brightnessSlider?.value || 80,
            screenTimeout: document.getElementById('screen-timeout')?.value || 'never'
        };
        
        // Save to localStorage (in production, save to server)
        localStorage.setItem('carStereoSettings', JSON.stringify(settings));
        
        alert('Settings saved!');
    });
}

// Reset settings
const resetBtn = document.getElementById('reset-settings-btn');
if (resetBtn) {
    resetBtn.addEventListener('click', () => {
        if (confirm('Reset all settings to defaults?')) {
            localStorage.removeItem('carStereoSettings');
            location.reload();
        }
    });
}

// Load settings
function loadSettings() {
    const saved = localStorage.getItem('carStereoSettings');
    if (saved) {
        try {
            const settings = JSON.parse(saved);
            if (defaultVolumeSlider) defaultVolumeSlider.value = settings.defaultVolume || 50;
            if (defaultVolumeValue) defaultVolumeValue.textContent = `${settings.defaultVolume || 50}%`;
            if (brightnessSlider) brightnessSlider.value = settings.brightness || 80;
            if (brightnessValue) brightnessValue.textContent = `${settings.brightness || 80}%`;
            const audioOutput = document.getElementById('audio-output');
            if (audioOutput) audioOutput.value = settings.audioOutput || 'bluetooth';
            const screenTimeout = document.getElementById('screen-timeout');
            if (screenTimeout) screenTimeout.value = settings.screenTimeout || 'never';
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }
}

// Update sensor info
async function updateSensorInfo() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.sense_hat_data) {
            const tempElement = document.getElementById('sys-temp');
            const humidityElement = document.getElementById('sys-humidity');
            const pressureElement = document.getElementById('sys-pressure');
            
            if (tempElement) {
                tempElement.textContent = `${data.sense_hat_data.temperature}°C`;
            }
            if (humidityElement) {
                humidityElement.textContent = `${data.sense_hat_data.humidity}%`;
            }
            if (pressureElement && data.sense_hat_data.pressure) {
                pressureElement.textContent = `${data.sense_hat_data.pressure} hPa`;
            }
        }
    } catch (error) {
        console.error('Error updating sensor info:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    updateSensorInfo();
    setInterval(updateSensorInfo, 5000);
});

