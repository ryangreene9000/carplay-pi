"""
Phone Location Module
Provides GPS location from connected phone (iPhone or Android)

Location retrieval strategy:
- iPhone: Web-based bridge that posts location to REST endpoint
- Android: BLE GATT characteristic for GPS data (future implementation)

This module provides a unified interface regardless of phone type.
"""

import time
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import BluetoothManager for device type detection
try:
    from modules.bluetooth_module import BluetoothManager, BLEAK_AVAILABLE
except ImportError:
    from bluetooth_module import BluetoothManager, BLEAK_AVAILABLE


class PhoneLocation:
    """
    Unified phone location provider that handles both iPhone and Android devices.
    """
    
    # Storage for iPhone location (posted via REST endpoint)
    last_ios_location = None
    last_ios_timestamp = 0
    
    # Storage for Android location (received via BLE)
    last_android_location = None
    last_android_timestamp = 0
    
    # Location data expiry (seconds)
    LOCATION_EXPIRY = 60  # Consider location stale after 60 seconds
    
    # BLE GATT UUIDs for Android location service (custom implementation)
    # These would need to match a companion Android app
    ANDROID_LOCATION_SERVICE_UUID = "00001234-0000-1000-8000-00805f9b34fb"
    ANDROID_LOCATION_CHAR_UUID = "00001235-0000-1000-8000-00805f9b34fb"
    
    @classmethod
    def get_location(cls):
        """
        Get location from the connected phone.
        Automatically uses the appropriate method based on detected device type.
        
        Returns:
            dict with 'lat', 'lon', 'timestamp', 'source' keys, or None if unavailable
        """
        device_type = BluetoothManager.connected_device_type
        
        if device_type == 'android':
            return cls._get_android_location()
        elif device_type == 'iphone':
            return cls._get_ios_location()
        else:
            # Try both methods for unknown devices
            loc = cls._get_ios_location()
            if loc:
                return loc
            return cls._get_android_location()
    
    @classmethod
    def _get_ios_location(cls):
        """
        Get location from iPhone via the web bridge.
        The iPhone web app posts location to /api/phone/location endpoint.
        
        Returns:
            dict with 'lat', 'lon', 'timestamp', 'source' or None
        """
        if cls.last_ios_location is None:
            return None
        
        # Check if location is fresh enough
        age = time.time() - cls.last_ios_timestamp
        if age > cls.LOCATION_EXPIRY:
            logging.debug(f"iOS location is stale ({age:.0f}s old)")
            return None
        
        return {
            'lat': cls.last_ios_location.get('lat'),
            'lon': cls.last_ios_location.get('lon'),
            'accuracy': cls.last_ios_location.get('accuracy'),
            'timestamp': cls.last_ios_location.get('timestamp'),
            'age_seconds': age,
            'source': 'iphone_web'
        }
    
    @classmethod
    def _get_android_location(cls):
        """
        Get location from Android via BLE GATT characteristic.
        Requires a companion Android app that exposes location via BLE.
        
        Returns:
            dict with 'lat', 'lon', 'timestamp', 'source' or None
        """
        # First check if we have cached Android location
        if cls.last_android_location:
            age = time.time() - cls.last_android_timestamp
            if age <= cls.LOCATION_EXPIRY:
                return {
                    'lat': cls.last_android_location.get('lat'),
                    'lon': cls.last_android_location.get('lon'),
                    'accuracy': cls.last_android_location.get('accuracy'),
                    'timestamp': cls.last_android_location.get('timestamp'),
                    'age_seconds': age,
                    'source': 'android_ble'
                }
        
        # Try to read from BLE if bleak is available
        if BLEAK_AVAILABLE:
            try:
                loc = asyncio.run(cls._async_read_android_location())
                if loc:
                    cls.last_android_location = loc
                    cls.last_android_timestamp = time.time()
                    return {
                        **loc,
                        'age_seconds': 0,
                        'source': 'android_ble'
                    }
            except Exception as e:
                logging.debug(f"Android BLE location read failed: {e}")
        
        return None
    
    @classmethod
    async def _async_read_android_location(cls):
        """
        Async method to read location from Android BLE characteristic.
        
        The companion Android app should expose a BLE service with:
        - Service UUID: ANDROID_LOCATION_SERVICE_UUID
        - Characteristic UUID: ANDROID_LOCATION_CHAR_UUID
        - Data format: "lat,lon,accuracy" as UTF-8 string
        
        Returns:
            dict with 'lat', 'lon', 'accuracy' or None
        """
        try:
            from bleak import BleakClient
            
            # Get connected device address from BluetoothManager
            bt = BluetoothManager()
            if not bt.connected_device:
                return None
            
            async with BleakClient(bt.connected_device) as client:
                if not client.is_connected:
                    return None
                
                # Try to read location characteristic
                try:
                    data = await client.read_gatt_char(cls.ANDROID_LOCATION_CHAR_UUID)
                    if data:
                        # Parse "lat,lon,accuracy" format
                        text = data.decode('utf-8').strip()
                        parts = text.split(',')
                        if len(parts) >= 2:
                            return {
                                'lat': float(parts[0]),
                                'lon': float(parts[1]),
                                'accuracy': float(parts[2]) if len(parts) > 2 else None,
                                'timestamp': time.time()
                            }
                except Exception as e:
                    logging.debug(f"Could not read Android location characteristic: {e}")
                
        except Exception as e:
            logging.debug(f"Android BLE connection failed: {e}")
        
        return None
    
    @classmethod
    def update_ios_location(cls, lat, lon, accuracy=None, timestamp=None):
        """
        Update the cached iOS location (called by the REST endpoint).
        
        Args:
            lat: Latitude as float
            lon: Longitude as float
            accuracy: Location accuracy in meters (optional)
            timestamp: ISO timestamp string (optional)
        """
        cls.last_ios_location = {
            'lat': float(lat),
            'lon': float(lon),
            'accuracy': accuracy,
            'timestamp': timestamp or time.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        cls.last_ios_timestamp = time.time()
        logging.info(f"Updated iOS location: {lat}, {lon}")
    
    @classmethod
    def update_android_location(cls, lat, lon, accuracy=None, timestamp=None):
        """
        Update the cached Android location (can be called externally if needed).
        
        Args:
            lat: Latitude as float
            lon: Longitude as float
            accuracy: Location accuracy in meters (optional)
            timestamp: ISO timestamp string (optional)
        """
        cls.last_android_location = {
            'lat': float(lat),
            'lon': float(lon),
            'accuracy': accuracy,
            'timestamp': timestamp or time.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        cls.last_android_timestamp = time.time()
        logging.info(f"Updated Android location: {lat}, {lon}")
    
    @classmethod
    def get_status(cls):
        """
        Get the current status of phone location providers.
        
        Returns:
            dict with status information
        """
        ios_age = time.time() - cls.last_ios_timestamp if cls.last_ios_location else None
        android_age = time.time() - cls.last_android_timestamp if cls.last_android_location else None
        
        return {
            'device_type': BluetoothManager.connected_device_type,
            'device_name': BluetoothManager.connected_device_name,
            'ios_location_available': cls.last_ios_location is not None and (ios_age or 999) < cls.LOCATION_EXPIRY,
            'ios_location_age': ios_age,
            'android_location_available': cls.last_android_location is not None and (android_age or 999) < cls.LOCATION_EXPIRY,
            'android_location_age': android_age,
            'ble_available': BLEAK_AVAILABLE
        }
    
    @classmethod
    def clear_all(cls):
        """Clear all cached location data."""
        cls.last_ios_location = None
        cls.last_ios_timestamp = 0
        cls.last_android_location = None
        cls.last_android_timestamp = 0

