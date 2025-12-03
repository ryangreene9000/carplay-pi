#!/usr/bin/env python3
"""
Car Stereo System - Main Application
Raspberry Pi 5 with Sense HAT and 7" Touch Screen
"""

from flask import Flask, render_template, jsonify, request
import threading
import time
import os
import subprocess
import platform
from modules.sense_hat_module import SenseHATManager
from modules.bluetooth_module import BluetoothManager
from modules.music_module import MusicManager
from modules.map_module import MapManager
from modules.android_auto_module import AndroidAutoManager
from modules.carplay_module import CarPlayManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'car-stereo-secret-key-2025'

# Initialize managers
sense_hat = SenseHATManager()
bluetooth = BluetoothManager()
music = MusicManager()
map_manager = MapManager()
android_auto = AndroidAutoManager()
carplay = CarPlayManager()

# Global state
current_screen = 'main_menu'
system_state = {
    'music_playing': False,
    'bluetooth_connected': False,
    'current_track': None,
    'volume': 50
}

@app.route('/')
def index():
    """Main menu screen"""
    return render_template('main_menu.html')

@app.route('/music')
def music_screen():
    """Music player screen"""
    return render_template('music.html')

@app.route('/map')
def map_screen():
    """Map navigation screen"""
    return render_template('map.html')

@app.route('/android_auto')
def android_auto_screen():
    """Android Auto screen"""
    return render_template('android_auto.html')

@app.route('/settings')
def settings_screen():
    """Settings screen"""
    return render_template('settings.html')

@app.route('/carplay')
def carplay_screen():
    """CarPlay / Android Auto screen"""
    return render_template('carplay.html')

# API endpoints for system control
@app.route('/api/status')
def get_status():
    """Get current system status"""
    return jsonify({
        'music_playing': system_state['music_playing'],
        'bluetooth_connected': bluetooth.is_connected(),
        'current_track': system_state['current_track'],
        'volume': system_state['volume'],
        'sense_hat_data': sense_hat.get_sensor_data()
    })

@app.route('/api/music/play', methods=['POST'])
def play_music():
    """Start music playback"""
    result = music.play()
    system_state['music_playing'] = result['success']
    return jsonify(result)

@app.route('/api/music/pause', methods=['POST'])
def pause_music():
    """Pause music playback"""
    result = music.pause()
    system_state['music_playing'] = False
    return jsonify(result)

@app.route('/api/music/stop', methods=['POST'])
def stop_music():
    """Stop music playback"""
    result = music.stop()
    system_state['music_playing'] = False
    return jsonify(result)

@app.route('/api/music/volume', methods=['POST'])
def set_volume():
    """Set volume level"""
    data = request.json
    volume = data.get('volume', 50)
    volume = max(0, min(100, volume))  # Clamp between 0-100
    system_state['volume'] = volume
    result = music.set_volume(volume)
    return jsonify(result)

@app.route('/api/bluetooth/scan', methods=['POST'])
def scan_bluetooth():
    """Scan for Bluetooth devices"""
    devices = bluetooth.scan_devices()
    return jsonify({'devices': devices})

@app.route('/api/bluetooth/connect', methods=['POST'])
def connect_bluetooth():
    """Connect to Bluetooth device"""
    data = request.json
    device_address = data.get('address')
    result = bluetooth.connect(device_address)
    system_state['bluetooth_connected'] = result['success']
    return jsonify(result)

@app.route('/api/bluetooth/disconnect', methods=['POST'])
def disconnect_bluetooth():
    """Disconnect Bluetooth"""
    data = request.json or {}
    device_address = data.get('address')
    result = bluetooth.disconnect(device_address)
    system_state['bluetooth_connected'] = False
    return jsonify(result)

@app.route('/api/bluetooth/status')
def bluetooth_status():
    """Get current Bluetooth connection status"""
    return jsonify(bluetooth.get_status())

# =============================================================================
# Media Control Endpoints (using playerctl on Raspberry Pi)
# =============================================================================

def run_playerctl(*args):
    """
    Run a playerctl command and return (success, output).
    playerctl controls media players via D-Bus (works with Bluetooth A2DP).
    """
    # Check if we're on Linux (playerctl only works on Linux)
    if platform.system().lower() != 'linux':
        return False, "playerctl only available on Linux/Raspberry Pi"
    
    cmd = ["playerctl"] + list(args)
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=5)
        return True, out.strip()
    except subprocess.CalledProcessError as e:
        print(f"playerctl error: {e.output}")
        return False, e.output.strip() if e.output else "Command failed"
    except FileNotFoundError:
        return False, "playerctl not installed. Run: sudo apt-get install playerctl"
    except subprocess.TimeoutExpired:
        return False, "playerctl command timed out"
    except Exception as e:
        return False, str(e)

@app.route('/api/media/play', methods=['POST'])
def api_media_play():
    """Send play command to connected media player"""
    ok, out = run_playerctl("play")
    return jsonify({"ok": ok, "output": out}), (200 if ok else 500)

@app.route('/api/media/pause', methods=['POST'])
def api_media_pause():
    """Send pause command to connected media player"""
    ok, out = run_playerctl("pause")
    return jsonify({"ok": ok, "output": out}), (200 if ok else 500)

@app.route('/api/media/toggle', methods=['POST'])
def api_media_toggle():
    """Toggle play/pause on connected media player"""
    ok, out = run_playerctl("play-pause")
    return jsonify({"ok": ok, "output": out}), (200 if ok else 500)

@app.route('/api/media/next', methods=['POST'])
def api_media_next():
    """Skip to next track on connected media player"""
    ok, out = run_playerctl("next")
    return jsonify({"ok": ok, "output": out}), (200 if ok else 500)

@app.route('/api/media/previous', methods=['POST'])
def api_media_previous():
    """Go to previous track on connected media player"""
    ok, out = run_playerctl("previous")
    return jsonify({"ok": ok, "output": out}), (200 if ok else 500)

@app.route('/api/media/status')
def api_media_status():
    """Get current playback status from connected media player"""
    ok_status, status = run_playerctl("status")
    ok_artist, artist = run_playerctl("metadata", "artist")
    ok_title, title = run_playerctl("metadata", "title")
    ok_album, album = run_playerctl("metadata", "album")
    
    # Determine if we have a valid player
    has_player = ok_status and status.lower() not in ['no players found', 'no player could handle this command']
    
    return jsonify({
        "ok": has_player,
        "status": status if ok_status else "No player",
        "artist": artist if ok_artist else "",
        "title": title if ok_title else "",
        "album": album if ok_album else "",
        "is_playing": status.lower() == "playing" if ok_status else False
    })

@app.route('/api/map/route', methods=['POST'])
def get_route():
    """Get route from map manager"""
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')
    route = map_manager.get_route(origin, destination)
    return jsonify(route)

@app.route('/api/android_auto/start', methods=['POST'])
def start_android_auto():
    """Start Android Auto service"""
    result = android_auto.start()
    return jsonify(result)

@app.route('/api/android_auto/stop', methods=['POST'])
def stop_android_auto():
    """Stop Android Auto service"""
    result = android_auto.stop()
    return jsonify(result)

# CarPlay API endpoints
@app.route('/api/carplay/status')
def get_carplay_status():
    """Get CarPlay status"""
    return jsonify(carplay.get_status())

@app.route('/api/carplay/start', methods=['POST'])
def start_carplay():
    """Start CarPlay engine"""
    data = request.json or {}
    fullscreen = data.get('fullscreen', True)
    result = carplay.start(fullscreen=fullscreen)
    return jsonify(result)

@app.route('/api/carplay/stop', methods=['POST'])
def stop_carplay():
    """Stop CarPlay engine"""
    result = carplay.stop()
    return jsonify(result)

@app.route('/api/carplay/restart', methods=['POST'])
def restart_carplay():
    """Restart CarPlay engine"""
    result = carplay.restart()
    return jsonify(result)

@app.route('/api/carplay/key', methods=['POST'])
def send_carplay_key():
    """Send navigation key to CarPlay"""
    data = request.json or {}
    key = data.get('key', '')
    result = carplay.send_key(key)
    return jsonify(result)

def update_sense_hat_display():
    """Background thread to update Sense HAT display"""
    while True:
        try:
            sense_hat.update_display(system_state)
            time.sleep(1)
        except Exception as e:
            print(f"Sense HAT update error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    # Start Sense HAT update thread
    sense_hat_thread = threading.Thread(target=update_sense_hat_display, daemon=True)
    sense_hat_thread.start()
    
    # Run Flask app
    # Use 0.0.0.0 to allow access from network, port 5000
    # For production, consider using a different port or reverse proxy
    # Use port 5001 on macOS (5000 is used by AirPlay), 5000 on Pi
    import sys
    port = 5001 if sys.platform == 'darwin' else 5000
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)

