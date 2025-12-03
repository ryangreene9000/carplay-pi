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
        """Async method to perform BLE scan with improved name detection."""
        results = []
        seen_addresses = set()
        
        try:
            print(f"Starting Bluetooth LE scan (timeout: {timeout}s)...")
            
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
