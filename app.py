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
# Targets the active AVRCP/BlueZ media player for Bluetooth audio control
# =============================================================================

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def get_active_player():
    """
    Get the first active media player (usually the BlueZ AVRCP player).
    Returns the player name or None if no players are available.
    """
    # Check if we're on Linux
    if platform.system().lower() != 'linux':
        return None
    
    try:
        out = subprocess.check_output(
            ["playerctl", "-l"], 
            stderr=subprocess.STDOUT, 
            text=True, 
            timeout=5
        ).strip()
        players = [p for p in out.splitlines() if p]
        if players:
            # Prefer bluez/bluetooth players
            for player in players:
                if 'bluez' in player.lower() or 'bluetooth' in player.lower():
                    logging.debug(f"Active player (Bluetooth): {player}")
                    return player
            # Fall back to first available player
            logging.debug(f"Active player: {players[0]}")
            return players[0]
        logging.debug("No active players found")
        return None
    except subprocess.CalledProcessError as e:
        logging.debug(f"playerctl -l error: {e.output if e.output else 'No output'}")
        return None
    except FileNotFoundError:
        logging.debug("playerctl not installed")
        return None
    except Exception as e:
        logging.debug(f"Error getting active player: {e}")
        return None

def run_playerctl_command(command):
    """
    Run a playerctl command targeting the active player.
    Returns (success, message).
    """
    # Check if we're on Linux
    if platform.system().lower() != 'linux':
        return False, "Media controls only available on Raspberry Pi"
    
    player = get_active_player()
    if not player:
        return False, "No active media player found (is your phone connected and playing?)"
    
    try:
        cmd = ["playerctl", "-p", player, command]
        logging.debug(f"Running: {' '.join(cmd)}")
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=5)
        return True, out.strip() if out.strip() else "OK"
    except subprocess.CalledProcessError as e:
        error_msg = e.output.strip() if e.output else "Command failed"
        logging.debug(f"playerctl error: {error_msg}")
        return False, error_msg
    except FileNotFoundError:
        return False, "playerctl not installed"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

@app.route('/api/media/play', methods=['POST'])
def api_media_play():
    """Send play command to connected media player"""
    ok, msg = run_playerctl_command("play")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

@app.route('/api/media/pause', methods=['POST'])
def api_media_pause():
    """Send pause command to connected media player"""
    ok, msg = run_playerctl_command("pause")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

@app.route('/api/media/toggle', methods=['POST'])
def api_media_toggle():
    """Toggle play/pause on connected media player"""
    ok, msg = run_playerctl_command("play-pause")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

@app.route('/api/media/next', methods=['POST'])
def api_media_next():
    """Skip to next track on connected media player"""
    ok, msg = run_playerctl_command("next")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

@app.route('/api/media/previous', methods=['POST'])
def api_media_previous():
    """Go to previous track on connected media player"""
    ok, msg = run_playerctl_command("previous")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

@app.route('/api/media/status')
def api_media_status():
    """Get current playback status from connected media player"""
    player = get_active_player()
    
    if not player:
        return jsonify({
            "ok": False,
            "status": "no-player",
            "message": "No media player connected",
            "artist": "",
            "title": "",
            "album": "",
            "is_playing": False
        })
    
    def pc(*args):
        """Helper to run playerctl with the active player."""
        try:
            cmd = ["playerctl", "-p", player] + list(args)
            return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=5).strip()
        except:
            return ""
    
    status = pc("status")
    artist = pc("metadata", "artist")
    title = pc("metadata", "title")
    album = pc("metadata", "album")
    
    return jsonify({
        "ok": True,
        "status": status or "Unknown",
        "artist": artist,
        "title": title,
        "album": album,
        "is_playing": status.lower() == "playing" if status else False,
        "player": player
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

