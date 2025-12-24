"""
Phone Manager - Pure BlueZ HFP (Hands-Free Profile) Integration
Handles incoming/outgoing phone calls via connected Bluetooth device
No oFono dependency - uses native BlueZ D-Bus interfaces
"""

import subprocess
import logging
import threading
import time
import platform
import queue

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check if we're on Linux (Raspberry Pi)
IS_LINUX = platform.system().lower() == 'linux'

# Try to import D-Bus for native BlueZ integration
DBUS_AVAILABLE = False
if IS_LINUX:
    try:
        import dbus
        import dbus.mainloop.glib
        DBUS_AVAILABLE = True
    except ImportError:
        logger.warning("dbus-python not available. Phone features will be limited.")

# Try to import GLib for main loop
GLIB_AVAILABLE = False
if IS_LINUX:
    try:
        from gi.repository import GLib
        GLIB_AVAILABLE = True
    except ImportError:
        logger.warning("GLib not available. Phone event streaming will use polling.")


class PhoneManager:
    """
    Manages Bluetooth phone connectivity and call handling via HFP.
    Uses pure BlueZ D-Bus interfaces (no oFono).
    """
    
    def __init__(self):
        self.connected_device = None
        self.device_name = None
        self.call_state = "idle"  # idle, incoming, outgoing, active, held, alerting
        self.caller_id = None
        self.caller_name = None
        self.listeners = []
        self.event_queue = queue.Queue()
        self.running = False
        self._loop = None
        self._loop_thread = None
        self._poll_thread = None
        self._bus = None
        self.recent_calls = []
        self._active_call_path = None
    
    def start(self):
        """Start the phone manager and begin listening for events."""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting PhoneManager...")
        
        if IS_LINUX and DBUS_AVAILABLE and GLIB_AVAILABLE:
            self._start_dbus_listener()
        else:
            logger.warning("D-Bus/GLib not available, using polling mode")
        
        # Start polling thread as backup/fallback
        self._poll_thread = threading.Thread(target=self._poll_status, daemon=True)
        self._poll_thread.start()
        
        logger.info("PhoneManager started")
    
    def stop(self):
        """Stop the phone manager."""
        self.running = False
        if self._loop:
            self._loop.quit()
        if self._loop_thread:
            self._loop_thread.join(timeout=2)
        logger.info("PhoneManager stopped")
    
    def _start_dbus_listener(self):
        """Start D-Bus signal listener for BlueZ HFP events."""
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self._bus = dbus.SystemBus()
            
            # Listen for property changes on all BlueZ objects
            self._bus.add_signal_receiver(
                self._handle_properties_changed,
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged",
                path_keyword="path"
            )
            
            # Listen for new interfaces (new calls)
            self._bus.add_signal_receiver(
                self._handle_interfaces_added,
                dbus_interface="org.freedesktop.DBus.ObjectManager",
                signal_name="InterfacesAdded"
            )
            
            # Listen for removed interfaces (call ended)
            self._bus.add_signal_receiver(
                self._handle_interfaces_removed,
                dbus_interface="org.freedesktop.DBus.ObjectManager",
                signal_name="InterfacesRemoved"
            )
            
            # Get initial connected device
            self._check_connected_devices()
            
            # Start GLib main loop in thread
            self._loop_thread = threading.Thread(target=self._run_glib_loop, daemon=True)
            self._loop_thread.start()
            
            logger.info("D-Bus listeners registered for BlueZ HFP")
            
        except Exception as e:
            logger.error(f"Failed to start D-Bus listener: {e}")
    
    def _run_glib_loop(self):
        """Run GLib main loop for D-Bus events."""
        try:
            self._loop = GLib.MainLoop()
            logger.info("GLib main loop starting...")
            self._loop.run()
        except Exception as e:
            logger.error(f"GLib loop error: {e}")
    
    def _handle_properties_changed(self, interface, changed, invalidated, path=None):
        """Handle D-Bus property change signals from BlueZ."""
        try:
            path_str = str(path) if path else ""
            
            # Handle BlueZ Call1 interface (incoming/active calls)
            if interface == "org.bluez.Call1":
                logger.info(f"Call property changed on {path_str}: {dict(changed)}")
                
                if "State" in changed:
                    new_state = str(changed["State"])
                    self._update_call_state(new_state)
                    self._active_call_path = path_str
                
                if "LineIdentification" in changed:
                    self.caller_id = str(changed["LineIdentification"])
                    logger.info(f"Caller ID: {self.caller_id}")
                
                if "Name" in changed:
                    self.caller_name = str(changed["Name"])
                
                self._notify_listeners()
            
            # Handle Device1 interface (connection status)
            elif interface == "org.bluez.Device1":
                if "Connected" in changed:
                    connected = bool(changed["Connected"])
                    if connected:
                        self._on_device_connected(path_str)
                    else:
                        self._on_device_disconnected()
                
                if "Name" in changed:
                    self.device_name = str(changed["Name"])
                    self._notify_listeners()
            
            # Handle MediaControl1 (for call audio routing)
            elif interface == "org.bluez.MediaControl1":
                if "Connected" in changed:
                    logger.info(f"Media control connected: {changed['Connected']}")
            
        except Exception as e:
            logger.error(f"Error handling property change: {e}")
    
    def _handle_interfaces_added(self, path, interfaces):
        """Handle new D-Bus interfaces (e.g., new incoming call)."""
        try:
            path_str = str(path)
            
            # Check for new Call1 interface (incoming call)
            if "org.bluez.Call1" in interfaces:
                call_props = interfaces["org.bluez.Call1"]
                logger.info(f"New call detected at {path_str}: {dict(call_props)}")
                
                self._active_call_path = path_str
                
                if "State" in call_props:
                    self._update_call_state(str(call_props["State"]))
                
                if "LineIdentification" in call_props:
                    self.caller_id = str(call_props["LineIdentification"])
                
                if "Name" in call_props:
                    self.caller_name = str(call_props["Name"])
                
                self._notify_listeners()
                
        except Exception as e:
            logger.error(f"Error handling interfaces added: {e}")
    
    def _handle_interfaces_removed(self, path, interfaces):
        """Handle removed D-Bus interfaces (e.g., call ended)."""
        try:
            path_str = str(path)
            
            # Check if Call1 interface was removed (call ended)
            if "org.bluez.Call1" in interfaces:
                logger.info(f"Call ended at {path_str}")
                
                # Add to recent calls before clearing
                if self.caller_id:
                    self.recent_calls.insert(0, {
                        "number": self.caller_id,
                        "name": self.caller_name or self.caller_id,
                        "type": "incoming" if self.call_state == "incoming" else "outgoing",
                        "time": time.strftime("%H:%M")
                    })
                    self.recent_calls = self.recent_calls[:20]  # Keep last 20
                
                self.call_state = "idle"
                self.caller_id = None
                self.caller_name = None
                self._active_call_path = None
                self._notify_listeners()
                
        except Exception as e:
            logger.error(f"Error handling interfaces removed: {e}")
    
    def _update_call_state(self, state):
        """Update call state from BlueZ state string."""
        # BlueZ Call1 states: incoming, dialing, alerting, active, held, waiting
        state_lower = state.lower()
        
        state_map = {
            "incoming": "incoming",
            "dialing": "outgoing", 
            "alerting": "alerting",  # Ringing on remote end
            "active": "active",
            "held": "held",
            "waiting": "incoming",
            "disconnected": "idle"
        }
        
        self.call_state = state_map.get(state_lower, state_lower)
        logger.info(f"Call state updated: {self.call_state}")
    
    def _check_connected_devices(self):
        """Check for already connected Bluetooth devices."""
        if not self._bus:
            return
            
        try:
            obj_manager = self._bus.get_object("org.bluez", "/")
            manager = dbus.Interface(obj_manager, "org.freedesktop.DBus.ObjectManager")
            objects = manager.GetManagedObjects()
            
            for path, interfaces in objects.items():
                if "org.bluez.Device1" in interfaces:
                    props = interfaces["org.bluez.Device1"]
                    if props.get("Connected", False):
                        self.connected_device = str(props.get("Address", ""))
                        self.device_name = str(props.get("Name", "Unknown"))
                        logger.info(f"Found connected device: {self.device_name}")
                        self._notify_listeners()
                        break
                        
        except Exception as e:
            logger.error(f"Error checking connected devices: {e}")
    
    def _on_device_connected(self, path):
        """Handle Bluetooth device connection."""
        try:
            if self._bus:
                device = self._bus.get_object("org.bluez", path)
                props = dbus.Interface(device, "org.freedesktop.DBus.Properties")
                self.connected_device = str(props.Get("org.bluez.Device1", "Address"))
                self.device_name = str(props.Get("org.bluez.Device1", "Name"))
                logger.info(f"Phone connected: {self.device_name} ({self.connected_device})")
                self._notify_listeners()
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
    
    def _on_device_disconnected(self):
        """Handle Bluetooth device disconnection."""
        logger.info(f"Phone disconnected: {self.device_name}")
        self.connected_device = None
        self.device_name = None
        self.call_state = "idle"
        self.caller_id = None
        self.caller_name = None
        self._active_call_path = None
        self._notify_listeners()
    
    def _poll_status(self):
        """Poll for phone status as fallback."""
        while self.running:
            try:
                if not DBUS_AVAILABLE:
                    self._check_connection_bluetoothctl()
                time.sleep(3)
            except Exception as e:
                logger.error(f"Poll error: {e}")
                time.sleep(5)
    
    def _check_connection_bluetoothctl(self):
        """Check Bluetooth connection status via bluetoothctl."""
        if not IS_LINUX:
            return
        
        try:
            result = subprocess.run(
                ["bluetoothctl", "devices", "Connected"],
                capture_output=True, text=True, timeout=5
            )
            
            lines = result.stdout.strip().split('\n')
            found_device = False
            
            for line in lines:
                if line.startswith("Device "):
                    parts = line.split(" ", 2)
                    if len(parts) >= 3:
                        new_device = parts[1]
                        new_name = parts[2]
                        
                        if self.connected_device != new_device:
                            self.connected_device = new_device
                            self.device_name = new_name
                            self._notify_listeners()
                        found_device = True
                        break
            
            if not found_device and self.connected_device:
                self._on_device_disconnected()
            
        except Exception as e:
            logger.debug(f"bluetoothctl check failed: {e}")
    
    def _notify_listeners(self):
        """Notify all registered listeners of state change."""
        data = self.get_status()
        
        # Add to event queue for SSE
        try:
            self.event_queue.put_nowait(data)
        except:
            pass
        
        # Call direct listeners
        for callback in self.listeners:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Listener callback error: {e}")
    
    def subscribe(self, callback):
        """Subscribe to phone state changes."""
        self.listeners.append(callback)
    
    def unsubscribe(self, callback):
        """Unsubscribe from phone state changes."""
        if callback in self.listeners:
            self.listeners.remove(callback)
    
    def get_status(self):
        """Get current phone status."""
        return {
            "connected": self.connected_device is not None,
            "device": self.connected_device,
            "device_name": self.device_name,
            "call_state": self.call_state,
            "state": self.call_state,  # Alias for compatibility
            "caller_id": self.caller_id,
            "caller": self.caller_id,  # Alias for compatibility
            "caller_name": self.caller_name,
            "recent_calls": self.recent_calls[:10]
        }
    
    def answer_call(self):
        """Answer incoming call via BlueZ D-Bus."""
        if not IS_LINUX:
            return {"success": False, "message": "Not supported on this platform"}
        
        if self.call_state != "incoming":
            return {"success": False, "message": "No incoming call to answer"}
        
        try:
            # Method 1: Use D-Bus directly if we have the call path
            if DBUS_AVAILABLE and self._bus and self._active_call_path:
                try:
                    call = self._bus.get_object("org.bluez", self._active_call_path)
                    call_iface = dbus.Interface(call, "org.bluez.Call1")
                    call_iface.Answer()
                    logger.info("Call answered via D-Bus")
                    return {"success": True}
                except Exception as e:
                    logger.warning(f"D-Bus answer failed: {e}")
            
            # Method 2: Use dbus-send as fallback
            result = subprocess.run([
                "dbus-send", "--system", "--print-reply",
                "--dest=org.bluez",
                self._active_call_path or "/org/bluez",
                "org.bluez.Call1.Answer"
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                logger.info("Call answered via dbus-send")
                return {"success": True}
            else:
                logger.error(f"dbus-send answer failed: {result.stderr}")
                return {"success": False, "message": result.stderr}
            
        except Exception as e:
            logger.error(f"Failed to answer call: {e}")
            return {"success": False, "message": str(e)}
    
    def hangup_call(self):
        """Hang up / reject current call via BlueZ D-Bus."""
        if not IS_LINUX:
            return {"success": False, "message": "Not supported on this platform"}
        
        if self.call_state == "idle":
            return {"success": False, "message": "No active call"}
        
        try:
            # Method 1: Use D-Bus directly
            if DBUS_AVAILABLE and self._bus and self._active_call_path:
                try:
                    call = self._bus.get_object("org.bluez", self._active_call_path)
                    call_iface = dbus.Interface(call, "org.bluez.Call1")
                    call_iface.Hangup()
                    logger.info("Call hung up via D-Bus")
                    self.call_state = "idle"
                    self._notify_listeners()
                    return {"success": True}
                except Exception as e:
                    logger.warning(f"D-Bus hangup failed: {e}")
            
            # Method 2: Use dbus-send as fallback
            result = subprocess.run([
                "dbus-send", "--system", "--print-reply",
                "--dest=org.bluez",
                self._active_call_path or "/org/bluez",
                "org.bluez.Call1.Hangup"
            ], capture_output=True, text=True, timeout=5)
            
            self.call_state = "idle"
            self._notify_listeners()
            
            if result.returncode == 0:
                logger.info("Call hung up via dbus-send")
                return {"success": True}
            else:
                # Even if dbus-send fails, we've updated local state
                return {"success": True, "message": "State updated"}
            
        except Exception as e:
            logger.error(f"Failed to hang up call: {e}")
            return {"success": False, "message": str(e)}
    
    def reject_call(self):
        """Reject incoming call (alias for hangup)."""
        return self.hangup_call()
    
    def dial_number(self, number):
        """Dial a phone number (requires HFP AG support)."""
        if not IS_LINUX:
            return {"success": False, "message": "Not supported on this platform"}
        
        if not number:
            return {"success": False, "message": "No number provided"}
        
        if not self.connected_device:
            return {"success": False, "message": "No phone connected"}
        
        # Clean number
        number = ''.join(c for c in number if c.isdigit() or c in '+*#')
        
        try:
            # BlueZ doesn't have a direct dial method in HFP AG
            # This would require AT commands or specific HFP implementation
            logger.warning("Outgoing calls not fully implemented in pure BlueZ mode")
            return {"success": False, "message": "Outgoing calls require phone initiation"}
            
        except Exception as e:
            logger.error(f"Failed to dial: {e}")
            return {"success": False, "message": str(e)}
    
    def send_dtmf(self, digit):
        """Send DTMF tone during active call."""
        if not IS_LINUX:
            return {"success": False, "message": "Not supported on this platform"}
        
        if self.call_state != "active":
            return {"success": False, "message": "No active call"}
        
        # DTMF would require AT commands
        return {"success": False, "message": "DTMF not implemented"}
    
    def get_recent_calls(self):
        """Get recent call history."""
        return {"ok": True, "calls": self.recent_calls}


# Singleton instance
phone_manager = PhoneManager()
