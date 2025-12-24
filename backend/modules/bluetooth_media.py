"""
Bluetooth Media Module
Native BlueZ AVRCP MediaPlayer1 D-Bus interface for controlling phone media playback.
This works even when playerctl cannot detect the media player.
"""

import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Try to import dbus (only available on Linux)
try:
    import dbus
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    logging.warning("dbus-python not installed. BlueZ media control unavailable.")
    logging.warning("  Install with: pip install dbus-python")

# BlueZ D-Bus constants
BLUEZ_SERVICE = "org.bluez"
MEDIA_PLAYER_IFACE = "org.bluez.MediaPlayer1"
DBUS_PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
DBUS_OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"


def find_bluez_media_player():
    """
    Scan D-Bus for any org.bluez.MediaPlayer1 instances.
    This works even when playerctl cannot see the player.
    
    Returns:
        dbus.proxies.ProxyObject or None: The media player D-Bus object
    """
    if not DBUS_AVAILABLE:
        return None
    
    try:
        bus = dbus.SystemBus()
        obj_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE, "/"),
            DBUS_OBJECT_MANAGER_IFACE
        )
        
        managed_objects = obj_manager.GetManagedObjects()
        
        for path, interfaces in managed_objects.items():
            if MEDIA_PLAYER_IFACE in interfaces:
                logging.debug(f"Found BlueZ media player at: {path}")
                return bus.get_object(BLUEZ_SERVICE, path)
        
        logging.debug("No BlueZ MediaPlayer1 found on D-Bus")
        return None
        
    except dbus.exceptions.DBusException as e:
        logging.debug(f"D-Bus error finding media player: {e}")
        return None
    except Exception as e:
        logging.debug(f"Error finding media player: {e}")
        return None


def run_bluez_media_command(cmd):
    """
    Run a command on the BlueZ MediaPlayer1 interface.
    
    Args:
        cmd: Command name - 'Play', 'Pause', 'Next', 'Previous', 'Stop'
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not DBUS_AVAILABLE:
        return False, "dbus-python not installed"
    
    player = find_bluez_media_player()
    if not player:
        return False, "No Bluetooth media player found (is your phone connected and paired?)"
    
    try:
        iface = dbus.Interface(player, MEDIA_PLAYER_IFACE)
        
        # Get the method and call it
        method = getattr(iface, cmd)
        method()
        
        logging.debug(f"BlueZ media command '{cmd}' executed successfully")
        return True, f"{cmd} OK"
        
    except dbus.exceptions.DBusException as e:
        error_msg = str(e)
        logging.debug(f"D-Bus error executing {cmd}: {error_msg}")
        
        # Provide more helpful error messages
        if "UnknownMethod" in error_msg:
            return False, f"Command '{cmd}' not supported by this player"
        elif "NotConnected" in error_msg:
            return False, "Bluetooth device not connected"
        else:
            return False, f"D-Bus error: {error_msg}"
            
    except Exception as e:
        logging.debug(f"Error executing {cmd}: {e}")
        return False, str(e)


def get_bluez_metadata():
    """
    Get current track metadata from the BlueZ MediaPlayer1 interface.
    
    Returns:
        dict or None: Dictionary with 'status', 'title', 'artist', 'album' keys
    """
    if not DBUS_AVAILABLE:
        return None
    
    player = find_bluez_media_player()
    if not player:
        return None
    
    try:
        props = dbus.Interface(player, DBUS_PROPERTIES_IFACE)
        
        # Get player status
        try:
            status = props.Get(MEDIA_PLAYER_IFACE, "Status")
            status = str(status)
        except:
            status = "Unknown"
        
        # Get track metadata
        try:
            track = props.Get(MEDIA_PLAYER_IFACE, "Track")
            title = str(track.get("Title", "")) if track else ""
            artist = str(track.get("Artist", "")) if track else ""
            album = str(track.get("Album", "")) if track else ""
        except:
            title = ""
            artist = ""
            album = ""
        
        logging.debug(f"BlueZ metadata - Status: {status}, Title: {title}, Artist: {artist}")
        
        return {
            "status": status,
            "title": title,
            "artist": artist,
            "album": album,
            "is_playing": status.lower() == "playing"
        }
        
    except dbus.exceptions.DBusException as e:
        logging.debug(f"D-Bus error getting metadata: {e}")
        return None
    except Exception as e:
        logging.debug(f"Error getting metadata: {e}")
        return None


def is_bluez_player_available():
    """Check if a BlueZ media player is available."""
    return find_bluez_media_player() is not None

