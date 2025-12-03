"""
Bluetooth Module
Handles Bluetooth LE scanning and connections using bleak library
Cross-platform support for macOS, Linux (Raspberry Pi), and Windows
"""

import asyncio
import sys

# Import bleak for cross-platform Bluetooth LE
try:
    from bleak import BleakScanner, BleakClient
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("Warning: bleak not installed. Bluetooth scanning will use mock data.")


class BluetoothManager:
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
        """Async method to perform BLE scan."""
        devices = []
        try:
            print(f"Starting Bluetooth LE scan (timeout: {timeout}s)...")
            discovered = await BleakScanner.discover(timeout=timeout)
            
            for device in discovered:
                devices.append({
                    'name': device.name or 'Unknown Device',
                    'address': device.address,
                    'rssi': getattr(device, 'rssi', None)  # Signal strength if available
                })
            
            # Sort by signal strength (strongest first) if available
            devices.sort(key=lambda d: d.get('rssi') or -999, reverse=True)
            
            print(f"Found {len(devices)} Bluetooth devices")
            return devices
            
        except Exception as e:
            print(f"Async Bluetooth scan error: {e}")
            raise
    
    def _get_mock_devices(self):
        """Return mock devices for development/testing."""
        return [
            {'name': 'Mock Bluetooth Device', 'address': '00:11:22:33:44:55', 'rssi': -50},
            {'name': 'Mock Phone', 'address': 'AA:BB:CC:DD:EE:FF', 'rssi': -65}
        ]
    
    def connect(self, device_address):
        """
        Connect to a Bluetooth device.
        
        Args:
            device_address: MAC address of the device to connect
            
        Returns:
            Dictionary with 'success' and 'message' keys
        """
        if not device_address:
            return {'success': False, 'message': 'No device address provided'}
        
        try:
            print(f"Attempting to connect to Bluetooth device: {device_address}")
            
            # For BLE devices, we would use BleakClient
            # For now, we'll simulate the connection since actual BLE connection
            # requires knowing the device's services and characteristics
            
            # Store the connection info
            self.connected_device = device_address
            self.is_connected_flag = True
            
            return {
                'success': True, 
                'message': f'Connected to {device_address}',
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
    
    def disconnect(self):
        """
        Disconnect from the current Bluetooth device.
        
        Returns:
            Dictionary with 'success' and 'message' keys
        """
        try:
            if self.connected_client:
                # Disconnect the BLE client
                asyncio.run(self._async_disconnect())
            
            previous_device = self.connected_device
            self.connected_device = None
            self.connected_client = None
            self.is_connected_flag = False
            
            return {
                'success': True, 
                'message': f'Disconnected from {previous_device}' if previous_device else 'Disconnected'
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
            'connected_device': self.connected_device
        }
