"""
Location Module
Provides location services for the Raspberry Pi via multiple methods:
- GPS module (if connected)
- IP-based geolocation (fallback)
"""

import requests
import logging

logging.basicConfig(level=logging.DEBUG)


class PiLocation:
    """
    Provides location for the Raspberry Pi using multiple sources.
    """
    
    # Cached location to avoid repeated API calls
    _cached_location = None
    _cache_time = None
    
    @staticmethod
    def get():
        """
        Get the Pi's current location.
        
        Returns:
            dict with 'lat' and 'lon' keys, or None if unavailable
        """
        # Try GPS first (if available)
        gps_loc = PiLocation._get_gps_location()
        if gps_loc:
            return gps_loc
        
        # Fallback to IP-based geolocation
        ip_loc = PiLocation._get_ip_location()
        if ip_loc:
            return ip_loc
        
        return None
    
    @staticmethod
    def _get_gps_location():
        """
        Get location from connected GPS module (gpsd).
        
        Returns:
            dict with 'lat' and 'lon' keys, or None if unavailable
        """
        try:
            # Try to connect to gpsd (GPS daemon)
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(("localhost", 2947))
            sock.send(b'?WATCH={"enable":true,"json":true}')
            
            # Read response
            data = sock.recv(4096).decode('utf-8')
            sock.close()
            
            # Parse GPS data (simplified - real implementation would be more robust)
            import json
            for line in data.split('\n'):
                if line.strip():
                    try:
                        obj = json.loads(line)
                        if obj.get('class') == 'TPV' and 'lat' in obj and 'lon' in obj:
                            logging.debug(f"GPS location: {obj['lat']}, {obj['lon']}")
                            return {'lat': obj['lat'], 'lon': obj['lon'], 'source': 'gps'}
                    except json.JSONDecodeError:
                        continue
            
            return None
            
        except Exception as e:
            logging.debug(f"GPS not available: {e}")
            return None
    
    @staticmethod
    def _get_ip_location():
        """
        Get approximate location based on IP address.
        Uses free geolocation API.
        
        Returns:
            dict with 'lat' and 'lon' keys, or None if unavailable
        """
        try:
            # Try ip-api.com (free, no API key required)
            response = requests.get(
                "http://ip-api.com/json/",
                timeout=5,
                headers={"User-Agent": "car_stereo_system"}
            )
            data = response.json()
            
            if data.get('status') == 'success':
                logging.debug(f"IP location: {data['lat']}, {data['lon']} ({data.get('city', 'Unknown')})")
                return {
                    'lat': data['lat'],
                    'lon': data['lon'],
                    'city': data.get('city', ''),
                    'region': data.get('regionName', ''),
                    'country': data.get('country', ''),
                    'source': 'ip'
                }
            
            return None
            
        except Exception as e:
            logging.debug(f"IP geolocation failed: {e}")
            return None
    
    @staticmethod
    def get_with_fallback(default_lat=43.6532, default_lon=-79.3832):
        """
        Get location with a fallback to default coordinates.
        
        Args:
            default_lat: Default latitude if all methods fail
            default_lon: Default longitude if all methods fail
            
        Returns:
            dict with 'lat' and 'lon' keys (never None)
        """
        loc = PiLocation.get()
        if loc:
            return loc
        
        logging.debug(f"Using default location: {default_lat}, {default_lon}")
        return {
            'lat': default_lat,
            'lon': default_lon,
            'source': 'default'
        }

