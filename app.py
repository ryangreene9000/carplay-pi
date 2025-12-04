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

# CORS support for iPhone Safari GPS bridge
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    print("Warning: flask-cors not installed. iPhone GPS bridge may not work.")

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

# Enable CORS for iPhone Safari GPS bridge
if CORS_AVAILABLE:
    CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize managers
sense_hat = SenseHATManager()
bluetooth = BluetoothManager()
music = MusicManager()
map_manager = MapManager()
android_auto = AndroidAutoManager()

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

@app.route('/ios_bridge')
def ios_bridge():
    """
    Web-based GPS bridge for iPhone.
    Open this page on the iPhone's Safari browser to share location with the car stereo.
    """
    return render_template('ios_bridge.html')

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

# =============================================================================
# Location API Endpoints
# =============================================================================

@app.route('/api/location/phone')
def phone_location():
    """Get location from connected Bluetooth phone (iPhone or Android)"""
    try:
        from modules.phone_location import PhoneLocation
        loc = PhoneLocation.get_location()
        if loc:
            return jsonify({
                "ok": True,
                "lat": loc["lat"],
                "lon": loc["lon"],
                "accuracy": loc.get("accuracy"),
                "source": loc.get("source", "phone"),
                "age_seconds": loc.get("age_seconds", 0),
                "device_type": bluetooth.connected_device_type
            })
        return jsonify({"ok": False, "message": "Phone location not available"})
    except Exception as e:
        logging.error(f"Phone location error: {e}")
        return jsonify({"ok": False, "message": str(e)})

@app.route('/api/phone/location', methods=['POST'])
def update_phone_location():
    """
    Endpoint for iPhone web bridge to POST GPS location.
    Expected JSON: {"lat": <float>, "lon": <float>, "accuracy": <float>, "timestamp": "..."}
    """
    try:
        from modules.phone_location import PhoneLocation
        data = request.json or {}
        
        lat = data.get('lat')
        lon = data.get('lon')
        
        if lat is None or lon is None:
            return jsonify({"ok": False, "error": "Missing lat/lon"}), 400
        
        PhoneLocation.update_ios_location(
            lat=lat,
            lon=lon,
            accuracy=data.get('accuracy'),
            timestamp=data.get('timestamp')
        )
        
        return jsonify({"ok": True, "message": "Location updated"})
    except Exception as e:
        logging.error(f"Phone location update error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/phone/location/status')
def phone_location_status():
    """Get status of phone location providers"""
    try:
        from modules.phone_location import PhoneLocation
        return jsonify(PhoneLocation.get_status())
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/debug/gps', methods=['POST'])
def debug_gps():
    """Debug endpoint to verify iPhone GPS is being received"""
    data = request.json or {}
    logging.info(f"DEBUG GPS received: lat={data.get('lat')}, lon={data.get('lon')}, accuracy={data.get('accuracy')}")
    print(f"📍 DEBUG GPS: {data}")
    return jsonify({"status": "ok", "received": data})

@app.route('/api/location/pi')
def pi_location():
    """Get Pi's location via GPS or IP geolocation"""
    try:
        from modules.location_module import PiLocation
        loc = PiLocation.get()
        if loc:
            return jsonify({
                "ok": True,
                "lat": loc["lat"],
                "lon": loc["lon"],
                "source": loc.get("source", "unknown"),
                "city": loc.get("city", ""),
                "region": loc.get("region", "")
            })
        return jsonify({"ok": False, "message": "Could not determine location"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})

@app.route('/api/location/current')
def current_location():
    """Get best available location (phone -> Pi -> default)"""
    try:
        # Try phone location first (using PhoneLocation for iPhone/Android)
        from modules.phone_location import PhoneLocation
        phone_loc = PhoneLocation.get_location()
        if phone_loc:
            return jsonify({
                "ok": True,
                "lat": phone_loc["lat"],
                "lon": phone_loc["lon"],
                "accuracy": phone_loc.get("accuracy"),
                "source": phone_loc.get("source", "phone"),
                "device_type": bluetooth.connected_device_type
            })
        
        # Try Pi location (GPS or IP)
        from modules.location_module import PiLocation
        pi_loc = PiLocation.get()
        if pi_loc:
            return jsonify({
                "ok": True,
                "lat": pi_loc["lat"],
                "lon": pi_loc["lon"],
                "source": pi_loc.get("source", "pi"),
                "city": pi_loc.get("city", "")
            })
        
        # Fallback to default location
        return jsonify({
            "ok": True,
            "lat": 43.6532,
            "lon": -79.3832,
            "source": "default"
        })
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})

# =============================================================================
# Places Search API (Overpass for POI)
# =============================================================================

def compute_distance_meters(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in meters.
    """
    import math
    
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    lat1_r, lon1_r, lat2_r, lon2_r = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in meters
    r = 6371000
    
    return c * r

def meters_to_miles(meters):
    """Convert meters to miles."""
    return meters / 1609.344

@app.route('/api/places/nearby')
def places_nearby():
    """Search for places near a location using Overpass API"""
    import requests as req
    
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    place_type = request.args.get('type', 'fuel')  # fuel, restaurant, parking, hospital
    radius = request.args.get('radius', '5000')  # meters (default 5km)
    
    if not lat or not lon:
        return jsonify({"ok": False, "error": "Missing lat/lon parameters"})
    
    user_lat = float(lat)
    user_lon = float(lon)
    
    # Map place types to Overpass tags
    type_mapping = {
        'fuel': '["amenity"="fuel"]',
        'gas': '["amenity"="fuel"]',
        'restaurant': '["amenity"="restaurant"]',
        'food': '["amenity"~"restaurant|fast_food|cafe"]',
        'parking': '["amenity"="parking"]',
        'hospital': '["amenity"="hospital"]',
        'pharmacy': '["amenity"="pharmacy"]',
        'atm': '["amenity"="atm"]',
        'charging': '["amenity"="charging_station"]',
        'hotel': '["tourism"="hotel"]',
        'supermarket': '["shop"="supermarket"]'
    }
    
    # Human-readable type names
    type_names = {
        'fuel': 'Gas Stations',
        'gas': 'Gas Stations',
        'restaurant': 'Restaurants',
        'food': 'Food & Dining',
        'parking': 'Parking',
        'hospital': 'Hospitals',
        'pharmacy': 'Pharmacies',
        'atm': 'ATMs',
        'charging': 'EV Charging',
        'hotel': 'Hotels',
        'supermarket': 'Supermarkets'
    }
    
    tag = type_mapping.get(place_type, f'["amenity"="{place_type}"]')
    type_name = type_names.get(place_type, place_type.title())
    
    query = f"""
    [out:json][timeout:15];
    node
      {tag}
      (around:{radius},{lat},{lon});
    out body;
    """
    
    try:
        response = req.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers={"User-Agent": "car_stereo_system"},
            timeout=20
        )
        data = response.json()
        
        # Format results with distance calculation
        results = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            place_lat = element.get("lat")
            place_lon = element.get("lon")
            
            if place_lat is None or place_lon is None:
                continue
            
            # Calculate distance
            distance_m = compute_distance_meters(user_lat, user_lon, place_lat, place_lon)
            distance_mi = meters_to_miles(distance_m)
            
            # Get name (prefer brand + name combo for gas stations)
            brand = tags.get("brand", "")
            name = tags.get("name", "")
            if brand and name and brand != name:
                display_name = f"{brand} - {name}"
            elif brand:
                display_name = brand
            elif name:
                display_name = name
            else:
                display_name = f"Unnamed {type_name[:-1] if type_name.endswith('s') else type_name}"
            
            results.append({
                "lat": place_lat,
                "lon": place_lon,
                "name": display_name,
                "brand": brand,
                "address": tags.get("addr:street", ""),
                "city": tags.get("addr:city", ""),
                "type": place_type,
                "distance_m": round(distance_m, 1),
                "distance_mi": round(distance_mi, 2),
                "distance_text": f"{distance_mi:.1f} mi" if distance_mi >= 0.1 else f"{int(distance_m)} m"
            })
        
        # Sort by distance (closest first)
        results.sort(key=lambda x: x["distance_m"])
        
        return jsonify({
            "ok": True,
            "type": place_type,
            "type_name": type_name,
            "count": len(results),
            "results": results
        })
        
    except Exception as e:
        logging.error(f"Overpass API error: {e}")
        return jsonify({"ok": False, "error": str(e)})

@app.route('/api/route/to_place')
def route_to_place():
    """Get route from current location to a specific place"""
    start_lat = request.args.get('start_lat')
    start_lon = request.args.get('start_lon')
    dest_lat = request.args.get('lat')
    dest_lon = request.args.get('lon')
    dest_name = request.args.get('name', 'Destination')
    
    if not all([start_lat, start_lon, dest_lat, dest_lon]):
        return jsonify({"ok": False, "error": "Missing coordinates"})
    
    try:
        # Format as coordinate strings for map_manager
        origin = f"{start_lat}, {start_lon}"
        destination = f"{dest_lat}, {dest_lon}"
        
        # Get route from map manager
        route = map_manager.get_route(origin, destination)
        
        if route.get('success'):
            # Add destination name to response
            route['destination_name'] = dest_name
            route['ok'] = True
            return jsonify(route)
        else:
            return jsonify({
                "ok": False,
                "error": route.get('message', 'Route calculation failed')
            })
            
    except Exception as e:
        logging.error(f"Route to place error: {e}")
        return jsonify({"ok": False, "error": str(e)})

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

