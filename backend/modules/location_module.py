"""
Location Module
Provides location services for the Raspberry Pi via multiple methods:
1. GPS module (if connected) - most accurate
2. WiFi-based Google Geolocation - very accurate (~20-50m)
3. IP-based geolocation - fallback (~5km accuracy)
"""

import requests
import logging
from modules import geolocation

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class PiLocation:
    """
    Provides location for the Raspberry Pi using multiple sources.
    Priority: GPS -> WiFi Geolocation -> IP Geolocation
    """
    
    # Cached location to avoid repeated API calls
    _cached_location = None
    _cache_time = None
    
    @staticmethod
    def get():
        """
        Get the Pi's current location using best available method.
        
        Priority:
        1. GPS (if available)
        2. WiFi-based Google Geolocation (most accurate without GPS)
        3. IP-based geolocation (fallback)
        
        Returns:
            dict: {lat, lon, accuracy, source} or None if unavailable
        """
        # Try GPS first (if available)
        gps_loc = PiLocation._get_gps_location()
        if gps_loc:
            logger.info(f"Location from GPS: {gps_loc['lat']}, {gps_loc['lon']}")
            return gps_loc
        
        # Try WiFi-based Google Geolocation (primary method)
        wifi_loc = PiLocation._get_wifi_location()
        if wifi_loc:
            logger.info(f"Location from WiFi: {wifi_loc['lat']}, {wifi_loc['lon']} (±{wifi_loc.get('accuracy', '?')}m)")
            return wifi_loc
        
        # Fallback to IP-based geolocation
        logger.warning("WiFi geolocation failed, falling back to IP geolocation")
        ip_loc = PiLocation._get_ip_location()
        if ip_loc:
            logger.info(f"Location from IP: {ip_loc['lat']}, {ip_loc['lon']} (fallback)")
            return ip_loc
        
        logger.error("All location methods failed")
        return None
    
    @staticmethod
    def _get_wifi_location():
        """
        Get accurate location using WiFi-based Google Geolocation API.
        
        Returns:
            dict: {lat, lon, accuracy, source, wifi_count} or None
        """
        try:
            result = geolocation.get_accurate_location()
            
            if result.get('ok'):
                logger.debug(f"WiFi scan found {result.get('wifi_count', 0)} networks")
                logger.debug(f"Google Geolocation accuracy: {result.get('accuracy')}m")
                return {
                    'lat': result['lat'],
                    'lon': result['lon'],
                    'accuracy': result.get('accuracy'),
                    'source': 'wifi_google',
                    'wifi_count': result.get('wifi_count', 0)
                }
            else:
                logger.warning(f"WiFi geolocation failed: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"WiFi geolocation exception: {e}")
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
            
            # Parse GPS data
            import json
            for line in data.split('\n'):
                if line.strip():
                    try:
                        obj = json.loads(line)
                        if obj.get('class') == 'TPV' and 'lat' in obj and 'lon' in obj:
                            logger.debug(f"GPS location: {obj['lat']}, {obj['lon']}")
                            return {
                                'lat': obj['lat'],
                                'lon': obj['lon'],
                                'accuracy': obj.get('epx', 10),  # GPS accuracy
                                'source': 'gps'
                            }
                    except json.JSONDecodeError:
                        continue
            
            return None
            
        except Exception as e:
            logger.debug(f"GPS not available: {e}")
            return None
    
    @staticmethod
    def _get_ip_location():
        """
        Get approximate location based on IP address.
        Uses ip-api.com as fallback when WiFi geolocation fails.
        
        Returns:
            dict: {lat, lon, accuracy, source, city} or None
        """
        try:
            logger.debug("Attempting IP-based geolocation fallback...")
            
            # Try ip-api.com (free, no API key required)
            response = requests.get(
                "http://ip-api.com/json/",
                timeout=5,
                headers={"User-Agent": "car_stereo_system"}
            )
            data = response.json()
            
            if data.get('status') == 'success':
                logger.debug(f"IP location: {data['lat']}, {data['lon']} ({data.get('city', 'Unknown')})")
                return {
                    'lat': data['lat'],
                    'lon': data['lon'],
                    'accuracy': 5000,  # IP geolocation is ~5km accurate
                    'city': data.get('city', ''),
                    'region': data.get('regionName', ''),
                    'country': data.get('country', ''),
                    'source': 'ip_fallback'
                }
            
            logger.warning(f"IP geolocation failed: {data.get('message', 'unknown error')}")
            return None
            
        except Exception as e:
            logger.error(f"IP geolocation exception: {e}")
            return None
    
    @staticmethod
    def get_with_fallback(default_lat=43.6532, default_lon=-79.3832):
        """
        Get location with a fallback to default coordinates.
        
        Args:
            default_lat: Default latitude if all methods fail
            default_lon: Default longitude if all methods fail
            
        Returns:
            dict: {lat, lon, accuracy, source} (never None)
        """
        loc = PiLocation.get()
        if loc:
            return loc
        
        logger.warning(f"Using default location: {default_lat}, {default_lon}")
        return {
            'lat': default_lat,
            'lon': default_lon,
            'accuracy': 100000,  # 100km - very inaccurate
            'source': 'default'
        }
