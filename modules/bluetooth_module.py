"""
Bluetooth Module
Handles Bluetooth LE scanning and connections using bleak library
Cross-platform support for macOS, Linux (Raspberry Pi), and Windows

Platform Notes:
- macOS: Uses CoreBluetooth via bleak (no extra setup needed)
- Linux/Raspberry Pi: Uses BlueZ via bleak (requires bluez package)
  - For A2DP audio: Uses bluetoothctl for pairing/connecting
- Windows: Uses WinRT via bleak (usually works out of the box)
"""

import asyncio
import platform
import subprocess
import sys

# Detect the operating system
SYSTEM_NAME = platform.system().lower()
IS_LINUX = SYSTEM_NAME == "linux"
IS_MACOS = SYSTEM_NAME == "darwin"
IS_WINDOWS = SYSTEM_NAME == "windows"

# Import bleak for cross-platform Bluetooth LE
try:
    from bleak import BleakScanner, BleakClient
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("Warning: bleak not installed. Bluetooth scanning will use mock data.")
    print("  Install with: pip install bleak>=0.22.0")
    if IS_LINUX:
        print("  On Raspberry Pi, also run: bash scripts/setup_rpi_bluetooth.sh")


class BluetoothManager:
    # Class-level storage for connected device type
    connected_device_type = 'unknown'  # 'iphone', 'android', or 'unknown'
    connected_device_name = None
    
    # Known manufacturer IDs for device detection
    APPLE_COMPANY_ID = 76        # 0x004C
    SAMSUNG_COMPANY_ID = 117
    GOOGLE_COMPANY_ID = 224
    MICROSOFT_COMPANY_ID = 6
    HUAWEI_COMPANY_ID = 637
    XIAOMI_COMPANY_ID = 343
    ONEPLUS_COMPANY_ID = 687
    
    def __init__(self):
        self.connected_device = None
        self.connected_client = None
        self.is_connected_flag = False
        self.scan_timeout = 5.0  # seconds
        
    def _get_event_loop(self):
        """Get or create an event loop that works in both sync and async contexts."""
        try:
            # Try to get the running loop
            loop = asyncio.get_running_loop()
            return loop
        except RuntimeError:
            # No running loop, create a new one
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            return asyncio.new_event_loop()
    
    def scan_devices(self, timeout=None):
        """
        Scan for available Bluetooth LE devices using bleak.
        
        Args:
            timeout: Scan duration in seconds (default: 5.0)
            
        Returns:
            List of dictionaries with 'name' and 'address' keys
        """
        if timeout is None:
            timeout = self.scan_timeout
            
        if not BLEAK_AVAILABLE:
            print("Bleak not available, returning mock devices")
            return self._get_mock_devices()
        
        try:
            # Run the async scan in a sync context
            devices = asyncio.run(self._async_scan(timeout))
            return devices
        except Exception as e:
            print(f"Bluetooth scan error: {e}")
            # Return empty list on error, not mock data (for production)
            return []
    
    async def _async_scan(self, timeout):
        """
        Async method to perform BLE scan with improved name detection.
        Works on both macOS (CoreBluetooth) and Linux/Raspberry Pi (BlueZ).
        """
        results = []
        seen_addresses = set()
        
        try:
            backend_info = "CoreBluetooth" if IS_MACOS else ("BlueZ" if IS_LINUX else "WinRT")
            print(f"Starting Bluetooth LE scan on {SYSTEM_NAME} ({backend_info})...")
            print(f"  Scan timeout: {timeout}s")
            
            # Use return_adv=True to get advertisement data with more device info
            discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
            
            for address, (device, adv_data) in discovered.items():
                # Try multiple sources for a readable name
                display_name = None
                
                # 1. Try the device name directly
                if device.name and device.name.strip():
                    display_name = device.name.strip()
                
                # 2. Try local_name from advertisement data
                if not display_name and adv_data:
                    local_name = getattr(adv_data, 'local_name', None)
                    if local_name and local_name.strip():
                        display_name = local_name.strip()
                
                # 3. Try manufacturer data to identify common devices
                if not display_name and adv_data:
                    mfr_data = getattr(adv_data, 'manufacturer_data', {})
                    if mfr_data:
                        # Apple devices (company ID 76 = 0x004C)
                        if 76 in mfr_data:
                            display_name = "Apple Device"
                        # Samsung (company ID 117)
                        elif 117 in mfr_data:
                            display_name = "Samsung Device"
                        # Microsoft (company ID 6)
                        elif 6 in mfr_data:
                            display_name = "Microsoft Device"
                        # Google (company ID 224)
                        elif 224 in mfr_data:
                            display_name = "Google Device"
                
                # 4. Fall back to Unknown Device
                if not display_name:
                    display_name = "Unknown Device"
                
                # Get address (avoid duplicates)
                device_address = getattr(device, 'address', None) or address or "unknown"
                
                if device_address in seen_addresses:
                    continue
                seen_addresses.add(device_address)
                
                # Get RSSI (signal strength)
                rssi = None
                if adv_data:
                    rssi = getattr(adv_data, 'rssi', None)
                if rssi is None:
                    rssi = getattr(device, 'rssi', None)
                
                results.append({
                    'name': display_name,
                    'address': device_address,
                    'rssi': rssi
                })
            
            # Sort: named devices first, then by signal strength
            results.sort(key=lambda d: (
                d['name'] == 'Unknown Device',  # Named devices first
                -(d.get('rssi') or -999)  # Then by signal strength
            ))
            
            # Count named vs unknown
            named_count = sum(1 for d in results if d['name'] != 'Unknown Device')
            print(f"Found {len(results)} Bluetooth devices ({named_count} with names)")
            
            return results
            
        except Exception as e:
            print(f"Async Bluetooth scan error: {e}")
            raise
    
    def _get_mock_devices(self):
        """Return mock devices for development/testing."""
        return [
            {'name': 'Mock Bluetooth Device', 'address': '00:11:22:33:44:55', 'rssi': -50},
            {'name': 'Mock Phone', 'address': 'AA:BB:CC:DD:EE:FF', 'rssi': -65}
        ]
    
    def _run_bluetoothctl(self, *commands):
        """
        Run a series of bluetoothctl commands non-interactively.
        
        Args:
            *commands: Commands to send to bluetoothctl
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            proc = subprocess.Popen(
                ["bluetoothctl"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send each command followed by newline; end with 'quit'
            for cmd in commands:
                proc.stdin.write(cmd + "\n")
            proc.stdin.write("quit\n")
            proc.stdin.flush()
            
            out, err = proc.communicate(timeout=30)
            return proc.returncode, out, err
            
        except subprocess.TimeoutExpired:
            proc.kill()
            return -1, "", "Timeout waiting for bluetoothctl"
        except FileNotFoundError:
            return -1, "", "bluetoothctl not found - install bluez package"
        except Exception as e:
            return -1, "", str(e)
    
    def connect(self, device_address):
        """
        Connect to a Bluetooth device.
        On Linux/Raspberry Pi, uses bluetoothctl for A2DP pairing.
        
        Args:
            device_address: MAC address of the device to connect
            
        Returns:
            Dictionary with 'success', 'message', and connection details
        """
        if not device_address:
            return {'success': False, 'message': 'No device address provided'}
        
        try:
            print(f"Attempting to connect to Bluetooth device: {device_address}")
            
            # On Linux, use bluetoothctl for real pairing/connecting
            if IS_LINUX:
                print("Using bluetoothctl for connection...")
                
                # Try pair + trust + connect
                rc, out, err = self._run_bluetoothctl(
                    f"pair {device_address}",
                    f"trust {device_address}",
                    f"connect {device_address}"
                )
                
                print(f"bluetoothctl output: {out}")
                if rc != 0:
                    print(f"bluetoothctl error: {err}")
                
                # Check if device is now connected
                connected = (
                    "Connected: yes" in out or 
                    "Connection successful" in out or
                    "already connected" in out.lower()
                )
                
                if connected:
                    self.connected_device = device_address
                    self.is_connected_flag = True
                    
                    # Detect device type from bluetoothctl output
                    # Look for device name in output
                    device_name = None
                    for line in out.split('\n'):
                        if 'Name:' in line:
                            device_name = line.split('Name:')[-1].strip()
                            break
                        elif 'Device' in line and device_address in line:
                            # Try to extract name from device line
                            parts = line.split(device_address)
                            if len(parts) > 1:
                                device_name = parts[-1].strip()
                    
                    BluetoothManager.set_connected_device_info(device_address, name=device_name)
                    
                    return {
                        'success': True,
                        'message': f'Connected to {device_address}',
                        'address': device_address,
                        'device_type': BluetoothManager.connected_device_type,
                        'raw_output': out
                    }
                else:
                    # Check for specific errors
                    if "Failed to pair" in out:
                        return {'success': False, 'message': 'Pairing failed - check phone for pairing request', 'raw_output': out}
                    elif "not available" in out.lower():
                        return {'success': False, 'message': 'Device not available - make sure it is nearby and discoverable', 'raw_output': out}
                    else:
                        return {'success': False, 'message': 'Connection failed', 'raw_output': out}
            
            else:
                # On macOS/Windows, use simulated connection for now
                # (BLE connection would require knowing device services)
                self.connected_device = device_address
                self.is_connected_flag = True
                
                return {
                    'success': True, 
                    'message': f'Connected to {device_address} (simulated on {SYSTEM_NAME})',
                    'address': device_address
                }
            
        except Exception as e:
            print(f"Bluetooth connect error: {e}")
            return {'success': False, 'message': str(e)}
    
    async def _async_connect(self, device_address):
        """Async method to connect to a BLE device."""
        try:
            client = BleakClient(device_address)
            await client.connect()
            
            if client.is_connected:
                self.connected_client = client
                self.connected_device = device_address
                self.is_connected_flag = True
                return True
            return False
        except Exception as e:
            print(f"Async connect error: {e}")
            raise
    
    def disconnect(self, device_address=None):
        """
        Disconnect from a Bluetooth device.
        On Linux/Raspberry Pi, uses bluetoothctl.
        
        Args:
            device_address: Optional address to disconnect. Uses connected device if not specified.
            
        Returns:
            Dictionary with 'success' and 'message' keys
        """
        try:
            address = device_address or self.connected_device
            
            if IS_LINUX and address:
                print(f"Disconnecting from {address} using bluetoothctl...")
                rc, out, err = self._run_bluetoothctl(f"disconnect {address}")
                print(f"bluetoothctl disconnect: {out}")
                
                disconnected = (
                    "Successful disconnected" in out or
                    "Successfully disconnected" in out or
                    "not connected" in out.lower()
                )
            
            elif self.connected_client:
                # Disconnect the BLE client
                asyncio.run(self._async_disconnect())
            
            previous_device = self.connected_device
            self.connected_device = None
            self.connected_client = None
            self.is_connected_flag = False
            
            # Clear device type info
            BluetoothManager.clear_connected_device_info()
            
            return {
                'success': True, 
                'message': f'Disconnected from {previous_device}' if previous_device else 'Disconnected',
                'address': address
            }
            
        except Exception as e:
            print(f"Bluetooth disconnect error: {e}")
            # Still mark as disconnected even on error
            self.connected_device = None
            self.connected_client = None
            self.is_connected_flag = False
            return {'success': True, 'message': 'Disconnected'}
    
    async def _async_disconnect(self):
        """Async method to disconnect from a BLE device."""
        try:
            if self.connected_client and self.connected_client.is_connected:
                await self.connected_client.disconnect()
        except Exception as e:
            print(f"Async disconnect error: {e}")
    
    def is_connected(self):
        """Check if a device is currently connected."""
        return self.is_connected_flag

    def get_connected_device(self):
        """Get the address of the currently connected device."""
        return self.connected_device
    
    def get_status(self):
        """Get current Bluetooth status."""
        return {
            'available': BLEAK_AVAILABLE,
            'connected': self.is_connected_flag,
            'connected_device': self.connected_device,
            'device_type': BluetoothManager.connected_device_type,
            'device_name': BluetoothManager.connected_device_name
        }
    
    @classmethod
    def detect_device_type(cls, device_name=None, manufacturer_id=None, device_address=None):
        """
        Detect if a device is an iPhone, Android, or unknown.
        
        Args:
            device_name: Name of the device (e.g., "John's iPhone")
            manufacturer_id: Bluetooth manufacturer ID from advertisement data
            device_address: MAC address (can help identify vendor)
            
        Returns:
            'iphone', 'android', or 'unknown'
        """
        device_type = 'unknown'
        
        # Check device name first (most reliable for named devices)
        if device_name:
            name_lower = device_name.lower()
            
            # iPhone/iPad detection
            if any(x in name_lower for x in ['iphone', 'ipad', 'apple', 'airpods', 'macbook', 'apple watch']):
                device_type = 'iphone'
            
            # Android device detection
            elif any(x in name_lower for x in [
                'pixel', 'galaxy', 'samsung', 'oneplus', 'android', 
                'huawei', 'xiaomi', 'redmi', 'poco', 'oppo', 'vivo',
                'motorola', 'moto', 'lg', 'sony', 'nokia', 'asus', 'rog'
            ]):
                device_type = 'android'
        
        # Check manufacturer ID if name didn't help
        if device_type == 'unknown' and manufacturer_id:
            # Apple
            if manufacturer_id == cls.APPLE_COMPANY_ID:
                device_type = 'iphone'
            # Android manufacturers
            elif manufacturer_id in [
                cls.SAMSUNG_COMPANY_ID, cls.GOOGLE_COMPANY_ID,
                cls.HUAWEI_COMPANY_ID, cls.XIAOMI_COMPANY_ID, cls.ONEPLUS_COMPANY_ID
            ]:
                device_type = 'android'
        
        # Check MAC address prefix for vendor (OUI)
        if device_type == 'unknown' and device_address:
            # Apple OUI prefixes (partial list)
            apple_prefixes = ['00:1C:B3', 'A4:D1:8C', 'A4:5E:60', '00:25:00', 
                              'E0:5F:45', 'F8:1E:DF', 'AC:BC:32', '28:6A:BA']
            # Samsung OUI prefixes
            samsung_prefixes = ['00:1D:F6', '00:1E:75', '58:CB:52', 'CC:07:AB']
            # Google OUI prefixes
            google_prefixes = ['F4:F5:D8', '54:60:09', '94:EB:2C']
            
            addr_upper = device_address.upper()[:8]
            
            if any(addr_upper.startswith(p) for p in apple_prefixes):
                device_type = 'iphone'
            elif any(addr_upper.startswith(p) for p in samsung_prefixes + google_prefixes):
                device_type = 'android'
        
        return device_type
    
    @classmethod
    def set_connected_device_info(cls, address, name=None, manufacturer_id=None):
        """
        Set the connected device info and detect its type.
        
        Args:
            address: MAC address of the connected device
            name: Device name if known
            manufacturer_id: Manufacturer ID from BLE advertisement
        """
        cls.connected_device_name = name
        cls.connected_device_type = cls.detect_device_type(
            device_name=name,
            manufacturer_id=manufacturer_id,
            device_address=address
        )
        print(f"Connected device detected as: {cls.connected_device_type} (name: {name})")
    
    @classmethod
    def clear_connected_device_info(cls):
        """Clear stored device info on disconnect."""
        cls.connected_device_type = 'unknown'
        cls.connected_device_name = None
    
    @staticmethod
    def get_phone_location():
        """
        Get location from the connected phone via Bluetooth.
        
        This is a stub implementation. Real location sharing would require:
        - iPhone: Location sharing via iCloud or a companion app
        - Android: Location sharing via GATT service or companion app
        
        For now, returns None. Future implementation could:
        - Use a BLE GATT characteristic for location data
        - Poll a companion app API
        - Use AVRCP metadata if phone shares location there
        
        Returns:
            dict with 'lat' and 'lon' keys, or None if unavailable
        """
        try:
            # Placeholder: In the future, this could:
            # 1. Check if connected device supports location service
            # 2. Read location from GATT characteristic
            # 3. Or query companion app API
            
            # For now, return None (phone location not yet implemented)
            return None
            
        except Exception as e:
            print(f"Phone location error: {e}")
            return None
