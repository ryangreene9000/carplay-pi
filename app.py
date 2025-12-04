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
import shutil

# =============================================================================
# Check for optional dependencies and warn if missing
# =============================================================================

# Check for folium (map features)
try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    print("Warning: folium is not installed. Map features may not work.")
    print("  Install with: pip install folium>=0.15.0")

# Check for bleak (Bluetooth LE)
try:
    import bleak
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("Warning: bleak is not installed. Bluetooth scanning will use mock data.")
    print("  Install with: pip install bleak>=0.22.0")

# Check for geopy (geocoding)
try:
    import geopy
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    print("Warning: geopy is not installed. Address geocoding will not work.")
    print("  Install with: pip install geopy>=2.4.1")

# Check for dbus-python (BlueZ native media control)
try:
    import dbus
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    print("Warning: dbus-python is not installed. Native BlueZ media control unavailable.")
    print("  Install with: pip install dbus-python")

# =============================================================================
# Import application modules
# =============================================================================

from modules.sense_hat_module import SenseHATManager
from modules.bluetooth_module import BluetoothManager
from modules.music_module import MusicManager
from modules.map_module import MapManager
from modules.android_auto_module import AndroidAutoManager
from modules.carplay_module import CarPlayManager

# Import BlueZ native media control (preferred over playerctl)
try:
    from modules.bluetooth_media import (
        run_bluez_media_command,
        get_bluez_metadata,
        is_bluez_player_available,
        DBUS_AVAILABLE as BLUEZ_MEDIA_AVAILABLE
    )
except ImportError:
    BLUEZ_MEDIA_AVAILABLE = False
    run_bluez_media_command = None
    get_bluez_metadata = None
    is_bluez_player_available = None

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
# Media Control Endpoints
# Auto-detects: playerctl (preferred) or BlueZ D-Bus AVRCP (fallback)
# =============================================================================

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Auto-detect if playerctl is installed
PLAYERCTL_EXISTS = shutil.which("playerctl") is not None
if PLAYERCTL_EXISTS:
    logging.info("playerctl detected - using as primary media controller")
else:
    logging.info("playerctl not found - will use BlueZ AVRCP fallback")

def run_media_command(bluez_cmd, playerctl_cmd):
    """
    Run a media command using the best available method:
    1. playerctl (if installed and working)
    2. BlueZ D-Bus AVRCP (fallback)
    
    Args:
        bluez_cmd: BlueZ MediaPlayer1 method name (e.g., 'Play', 'Pause')
        playerctl_cmd: playerctl command (e.g., 'play', 'pause')
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check if we're on Linux
    if platform.system().lower() != 'linux':
        return False, "Media controls only available on Raspberry Pi"
    
    # Try playerctl first if it exists
    if PLAYERCTL_EXISTS:
        logging.debug(f"Trying playerctl command: {playerctl_cmd}")
        try:
            out = subprocess.check_output(
                ["playerctl", playerctl_cmd],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=5
            )
            return True, out.strip() if out.strip() else "OK"
        except subprocess.CalledProcessError as e:
            error_msg = e.output.strip() if e.output else ""
            # If playerctl says no players, try BlueZ fallback
            if "no player" in error_msg.lower() or "no players" in error_msg.lower():
                logging.debug(f"playerctl: {error_msg}, trying BlueZ AVRCP fallback...")
            else:
                logging.debug(f"playerctl error: {error_msg}")
                # Still try BlueZ as fallback
        except Exception as e:
            logging.debug(f"playerctl exception: {e}, trying BlueZ fallback...")
    
    # Fallback to BlueZ native D-Bus control
    if BLUEZ_MEDIA_AVAILABLE and run_bluez_media_command:
        logging.debug(f"Trying BlueZ D-Bus command: {bluez_cmd}")
        ok, msg = run_bluez_media_command(bluez_cmd)
        if ok:
            return ok, msg
        return False, msg
    
    # Neither method available
    if not PLAYERCTL_EXISTS and not BLUEZ_MEDIA_AVAILABLE:
        return False, "No media controller available. Install playerctl or dbus-python."
    
    return False, "No active media player found (is your phone connected?)"

def get_active_player():
    """
    Get the first active media player via playerctl.
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
        logging.debug("No active players found via playerctl")
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
    Run a playerctl command targeting the active player (fallback method).
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
    ok, msg = run_media_command("Play", "play")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

@app.route('/api/media/pause', methods=['POST'])
def api_media_pause():
    """Send pause command to connected media player"""
    ok, msg = run_media_command("Pause", "pause")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

@app.route('/api/media/toggle', methods=['POST'])
def api_media_toggle():
    """Toggle play/pause on connected media player"""
    # BlueZ doesn't have a toggle, so we check status and send appropriate command
    if BLUEZ_MEDIA_AVAILABLE and get_bluez_metadata:
        metadata = get_bluez_metadata()
        if metadata:
            if metadata.get('is_playing'):
                return api_media_pause()
            else:
                return api_media_play()
    # Fall back to playerctl which has play-pause
    ok, msg = run_playerctl_command("play-pause")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

@app.route('/api/media/next', methods=['POST'])
def api_media_next():
    """Skip to next track on connected media player"""
    ok, msg = run_media_command("Next", "next")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

@app.route('/api/media/previous', methods=['POST'])
def api_media_previous():
    """Go to previous track on connected media player"""
    ok, msg = run_media_command("Previous", "previous")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 500)

@app.route('/api/media/status')
def api_media_status():
    """Get current playback status from connected media player"""
    
    # Try BlueZ native metadata first
    if BLUEZ_MEDIA_AVAILABLE and get_bluez_metadata:
        metadata = get_bluez_metadata()
        if metadata:
            return jsonify({
                "ok": True,
                "status": metadata.get("status", "Unknown"),
                "artist": metadata.get("artist", ""),
                "title": metadata.get("title", ""),
                "album": metadata.get("album", ""),
                "is_playing": metadata.get("is_playing", False),
                "source": "bluez"
            })
    
    # Fall back to playerctl
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
        "player": player,
        "source": "playerctl"
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

