"""
Map Module
Handles map display and navigation using OpenStreetMap and Google Maps API
Supports both coordinate input and street address geocoding
"""

import folium
import json
import os
import re
import ssl
import certifi
import requests
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Import config for API keys
try:
    from config import GOOGLE_MAPS_API_KEY, USE_GOOGLE_MAPS, USE_OSRM_FALLBACK
except ImportError:
    GOOGLE_MAPS_API_KEY = None
    USE_GOOGLE_MAPS = False
    USE_OSRM_FALLBACK = True

logging.basicConfig(level=logging.DEBUG)


class MapManager:
    def __init__(self):
        self.current_location = None
        self.map_file = 'static/map.html'
        self.default_center = [43.6532, -79.3832]  # Default: Toronto (adjust as needed)
        
        # Create SSL context with certifi certificates (fixes macOS SSL issues)
        ctx = ssl.create_default_context(cafile=certifi.where())
        
        # Initialize geocoder with a user agent and SSL context
        self.geolocator = Nominatim(
            user_agent="car_stereo_system_v1",
            ssl_context=ctx
        )
    
    def geocode_address(self, text):
        """
        Convert text to (latitude, longitude) coordinates.
        Accepts either street addresses OR coordinate pairs like "lat, lon".
        Uses Google Maps API if available, with Nominatim fallback.
        
        Args:
            text: Street address OR coordinate string (e.g., "40.78, -77.86")
            
        Returns:
            Tuple of (latitude, longitude) or None if failed
        """
        if not text or not isinstance(text, str):
            return None
        
        text = text.strip()
        
        # First, check if it's already coordinates
        if "," in text:
            try:
                parts = text.split(",")
                if len(parts) == 2:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        return (lat, lon)
            except (ValueError, IndexError):
                pass  # Not valid coords, try geocoding
        
        # Try Google Maps Geocoding API first (if available)
        if USE_GOOGLE_MAPS and GOOGLE_MAPS_API_KEY:
            result = self._google_geocode(text)
            if result:
                return result
        
        # Try official geopy geocoder
        try:
            location = self.geolocator.geocode(text, timeout=10)
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            logging.debug(f"Geopy geocoding error: {e}")
        
        # Fallback: direct Nominatim HTTP request
        try:
            import urllib.parse
            encoded_text = urllib.parse.quote(text)
            url = f"https://nominatim.openstreetmap.org/search?format=json&q={encoded_text}"
            headers = {"User-Agent": "car_stereo_system_v1"}
            response = requests.get(url, headers=headers, timeout=10)
            results = response.json()
            if results and len(results) > 0:
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                return (lat, lon)
        except Exception as e:
            logging.debug(f"Fallback geocoding error: {e}")
        
        return None
    
    def _google_geocode(self, address):
        """
        Geocode address using Google Maps Geocoding API.
        
        Args:
            address: Street address string
            
        Returns:
            Tuple of (latitude, longitude) or None if failed
        """
        try:
            import urllib.parse
            encoded_address = urllib.parse.quote(address)
            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={GOOGLE_MAPS_API_KEY}"
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                location = data['results'][0]['geometry']['location']
                logging.debug(f"Google geocode: {address} -> {location['lat']}, {location['lng']}")
                return (location['lat'], location['lng'])
            else:
                logging.debug(f"Google geocode failed: {data.get('status')}")
                return None
                
        except Exception as e:
            logging.debug(f"Google geocoding error: {e}")
            return None
    
    def geocode_address_strict(self, address):
        """
        Convert a street address to (latitude, longitude) coordinates.
        Raises ValueError if geocoding fails.
        
        Args:
            address: Street address string (e.g., "123 Main St, City, State")
            
        Returns:
            Tuple of (latitude, longitude)
            
        Raises:
            ValueError: If address cannot be geocoded
        """
        result = self.geocode_address(address)
        if result is None:
            raise ValueError(f"Could not geocode address: {address}")
        return result
    
    def parse_location_input(self, value):
        """
        Parse user input that could be either coordinates or a street address.
        Uses the robust geocode_address method with fallbacks.
        
        Args:
            value: String that is either:
                   - Coordinates like "40.78, -77.86" or "40.78,-77.86"
                   - Street address like "123 Main St, City, State"
                   
        Returns:
            Tuple of (latitude, longitude) as floats
            
        Raises:
            ValueError: If location cannot be parsed or geocoded
        """
        if not value or not isinstance(value, str):
            raise ValueError("Location input cannot be empty")
        
        result = self.geocode_address(value)
        if result is None:
            raise ValueError(f"Could not find location: {value}")
        return result
    
    def get_route(self, origin, destination):
        """
        Get route between two points using OSRM (Open Source Routing Machine).
        Accepts either coordinates or street addresses for both origin and destination.
        
        Args:
            origin: Starting point (coordinates string or street address)
            destination: End point (coordinates string or street address)
            
        Returns:
            Dictionary with route information including polyline and turn-by-turn steps
        """
        try:
            # Parse origin (could be coords or address)
            origin_coords = self.parse_location_input(origin)
            
            # Parse destination (could be coords or address)
            dest_coords = self.parse_location_input(destination)
            
            # Convert to list format for compatibility
            origin_list = list(origin_coords)
            dest_list = list(dest_coords)
            
            # Try Google Directions API first (if available)
            route_data = None
            if USE_GOOGLE_MAPS and GOOGLE_MAPS_API_KEY:
                route_data = self._get_google_route(origin_coords, dest_coords)
            
            # Fallback to OSRM if Google fails or is disabled
            if not route_data and USE_OSRM_FALLBACK:
                route_data = self._get_osrm_route(origin_coords, dest_coords)
            
            if route_data:
                return {
                    'success': True,
                    'origin': origin_list,
                    'origin_input': origin,
                    'destination': dest_list,
                    'destination_input': destination,
                    'distance': route_data['distance_text'],
                    'duration': route_data['duration_text'],
                    'distance_m': route_data['distance_m'],
                    'duration_s': route_data['duration_s'],
                    'polyline': route_data['polyline'],
                    'steps': route_data['steps'],
                    'waypoints': route_data['polyline']  # Full route path
                }
            
            # Fallback to simple straight-line calculation
            distance = self._calculate_distance(origin_coords, dest_coords)
            duration_hours = distance / 30
            duration_mins = int(duration_hours * 60)
            distance_m = distance * 1609.34
            duration_s = duration_mins * 60
            
            return {
                'success': True,
                'origin': origin_list,
                'origin_input': origin,
                'destination': dest_list,
                'destination_input': destination,
                'distance': f"{distance:.1f} miles",
                'duration': f"{duration_mins} mins" if duration_mins < 60 else f"{duration_hours:.1f} hours",
                'distance_m': distance_m,
                'duration_s': duration_s,
                'polyline': [origin_list, dest_list],
                'steps': [{
                    'instruction': f'Head toward destination ({distance:.1f} miles)',
                    'distance_m': distance_m,
                    'lat': dest_list[0],
                    'lon': dest_list[1]
                }],
                'waypoints': [origin_list, dest_list]
            }
        except ValueError as e:
            print(f"Route calculation error: {e}")
            return {
                'success': False,
                'message': str(e)
            }
        except Exception as e:
            print(f"Route calculation error: {e}")
            return {
                'success': False,
                'message': f"Error calculating route: {str(e)}"
            }
    
    def _get_google_route(self, origin_coords, dest_coords):
        """
        Get route from Google Directions API.
        Returns polyline coordinates and turn-by-turn directions.
        
        Args:
            origin_coords: Tuple of (lat, lon)
            dest_coords: Tuple of (lat, lon)
            
        Returns:
            Dictionary with route data or None if failed
        """
        try:
            origin_str = f"{origin_coords[0]},{origin_coords[1]}"
            dest_str = f"{dest_coords[0]},{dest_coords[1]}"
            
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                'origin': origin_str,
                'destination': dest_str,
                'key': GOOGLE_MAPS_API_KEY,
                'mode': 'driving',
                'units': 'imperial'
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get('status') != 'OK' or not data.get('routes'):
                logging.debug(f"Google Directions error: {data.get('status')}")
                return None
            
            route = data['routes'][0]
            leg = route['legs'][0]
            
            # Extract distance and duration
            distance_m = leg['distance']['value']  # meters
            duration_s = leg['duration']['value']  # seconds
            distance_text = leg['distance']['text']
            duration_text = leg['duration']['text']
            
            # Decode polyline
            encoded_polyline = route['overview_polyline']['points']
            polyline = self._decode_google_polyline(encoded_polyline)
            
            # Extract turn-by-turn steps
            steps = []
            for step in leg.get('steps', []):
                # Strip HTML tags from instructions
                import re
                instruction = re.sub('<[^<]+?>', '', step.get('html_instructions', ''))
                
                start_loc = step.get('start_location', {})
                
                steps.append({
                    'instruction': instruction,
                    'distance_m': step.get('distance', {}).get('value', 0),
                    'duration_s': step.get('duration', {}).get('value', 0),
                    'lat': start_loc.get('lat', 0),
                    'lon': start_loc.get('lng', 0),
                    'type': step.get('maneuver', 'continue'),
                    'modifier': ''
                })
            
            logging.debug(f"Google route: {distance_text}, {duration_text}, {len(steps)} steps")
            
            return {
                'distance_m': distance_m,
                'duration_s': duration_s,
                'distance_text': distance_text,
                'duration_text': duration_text,
                'polyline': polyline,
                'steps': steps
            }
            
        except Exception as e:
            logging.error(f"Google Directions error: {e}")
            return None
    
    def _decode_google_polyline(self, encoded):
        """
        Decode Google's encoded polyline format.
        
        Args:
            encoded: Encoded polyline string
            
        Returns:
            List of [lat, lon] coordinate pairs
        """
        points = []
        index = 0
        lat = 0
        lng = 0
        
        while index < len(encoded):
            # Decode latitude
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            lat += (~(result >> 1) if result & 1 else result >> 1)
            
            # Decode longitude
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            lng += (~(result >> 1) if result & 1 else result >> 1)
            
            points.append([lat / 1e5, lng / 1e5])
        
        return points
    
    def _get_osrm_route(self, origin_coords, dest_coords):
        """
        Get route from OSRM (Open Source Routing Machine) API.
        Returns polyline coordinates and turn-by-turn directions.
        
        Args:
            origin_coords: Tuple of (lat, lon)
            dest_coords: Tuple of (lat, lon)
            
        Returns:
            Dictionary with route data or None if failed
        """
        try:
            # OSRM uses lon,lat format (opposite of typical lat,lon)
            origin_str = f"{origin_coords[1]},{origin_coords[0]}"
            dest_str = f"{dest_coords[1]},{dest_coords[0]}"
            
            # Use public OSRM demo server (for production, use self-hosted)
            url = f"https://router.project-osrm.org/route/v1/driving/{origin_str};{dest_str}"
            params = {
                'overview': 'full',
                'geometries': 'geojson',
                'steps': 'true',
                'annotations': 'true'
            }
            
            response = requests.get(url, params=params, timeout=15, headers={
                'User-Agent': 'car_stereo_system_v1'
            })
            data = response.json()
            
            if data.get('code') != 'Ok' or not data.get('routes'):
                print(f"OSRM error: {data.get('code', 'Unknown')}")
                return None
            
            route = data['routes'][0]
            
            # Extract distance and duration
            distance_m = route.get('distance', 0)  # meters
            duration_s = route.get('duration', 0)  # seconds
            
            # Format for display
            distance_mi = distance_m / 1609.34
            duration_min = duration_s / 60
            
            if distance_mi < 0.1:
                distance_text = f"{int(distance_m)} m"
            else:
                distance_text = f"{distance_mi:.1f} miles"
            
            if duration_min < 1:
                duration_text = "< 1 min"
            elif duration_min < 60:
                duration_text = f"{int(duration_min)} mins"
            else:
                hours = int(duration_min // 60)
                mins = int(duration_min % 60)
                duration_text = f"{hours}h {mins}m"
            
            # Extract polyline coordinates (GeoJSON format: [lon, lat] -> [lat, lon])
            geometry = route.get('geometry', {})
            coords = geometry.get('coordinates', [])
            polyline = [[coord[1], coord[0]] for coord in coords]  # Convert to [lat, lon]
            
            # Extract turn-by-turn steps
            steps = []
            legs = route.get('legs', [])
            for leg in legs:
                for step in leg.get('steps', []):
                    maneuver = step.get('maneuver', {})
                    
                    # Build instruction text
                    instruction = self._build_instruction(step, maneuver)
                    
                    steps.append({
                        'instruction': instruction,
                        'distance_m': step.get('distance', 0),
                        'duration_s': step.get('duration', 0),
                        'lat': maneuver.get('location', [0, 0])[1],  # lon,lat -> lat
                        'lon': maneuver.get('location', [0, 0])[0],  # lon,lat -> lon
                        'type': maneuver.get('type', ''),
                        'modifier': maneuver.get('modifier', '')
                    })
            
            return {
                'distance_m': distance_m,
                'duration_s': duration_s,
                'distance_text': distance_text,
                'duration_text': duration_text,
                'polyline': polyline,
                'steps': steps
            }
            
        except Exception as e:
            print(f"OSRM route error: {e}")
            return None
    
    def _build_instruction(self, step, maneuver):
        """
        Build human-readable instruction from OSRM step data.
        
        Args:
            step: OSRM step object
            maneuver: OSRM maneuver object
            
        Returns:
            String instruction
        """
        maneuver_type = maneuver.get('type', '')
        modifier = maneuver.get('modifier', '')
        name = step.get('name', '')
        ref = step.get('ref', '')
        
        # Use road reference if name is empty
        road_name = name or ref or 'the road'
        
        # Build instruction based on maneuver type
        instructions = {
            'depart': f"Start on {road_name}",
            'arrive': f"Arrive at your destination",
            'turn': f"Turn {modifier} onto {road_name}",
            'new name': f"Continue onto {road_name}",
            'merge': f"Merge onto {road_name}",
            'on ramp': f"Take the ramp onto {road_name}",
            'off ramp': f"Take the exit onto {road_name}",
            'fork': f"Keep {modifier} onto {road_name}",
            'end of road': f"At the end of the road, turn {modifier} onto {road_name}",
            'continue': f"Continue on {road_name}",
            'roundabout': f"Enter the roundabout and take the exit onto {road_name}",
            'rotary': f"Enter the rotary and take the exit onto {road_name}",
            'roundabout turn': f"At the roundabout, turn {modifier}",
            'notification': f"Continue on {road_name}",
            'exit roundabout': f"Exit the roundabout onto {road_name}",
            'exit rotary': f"Exit the rotary onto {road_name}"
        }
        
        instruction = instructions.get(maneuver_type, f"Continue on {road_name}")
        
        # Clean up instruction
        instruction = instruction.replace('  ', ' ').strip()
        if instruction.endswith(' onto '):
            instruction = instruction[:-6]
        
        return instruction
    
    def _calculate_distance(self, coord1, coord2):
        """
        Calculate distance between two coordinates using Haversine formula.
        
        Args:
            coord1: Tuple of (lat, lon)
            coord2: Tuple of (lat, lon)
            
        Returns:
            Distance in miles
        """
        import math
        
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in miles
        r = 3956
        
        return c * r
    
    def create_map(self, center=None, zoom=13):
        """Create a new map centered at specified location"""
        if center is None:
            center = self.default_center
        
        try:
            # Create folium map
            m = folium.Map(
                location=center,
                zoom_start=zoom,
                tiles='OpenStreetMap'
            )
            
            # Save to static directory
            map_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'map.html')
            m.save(map_path)
            
            return {'success': True, 'map_file': 'static/map.html'}
        except Exception as e:
            print(f"Map creation error: {e}")
            return {'success': False, 'message': str(e)}
    
    def add_marker(self, location, popup_text=''):
        """Add marker to map"""
        try:
            # This would modify the existing map file
            # For simplicity, we'll recreate the map
            return {'success': True}
        except Exception as e:
            print(f"Add marker error: {e}")
            return {'success': False, 'message': str(e)}
    
    def update_location(self, latitude, longitude):
        """Update current location"""
        self.current_location = [latitude, longitude]
        return self.create_map(center=self.current_location)
    
    def reverse_geocode(self, latitude, longitude):
        """
        Convert coordinates to a street address.
        
        Args:
            latitude: Latitude as float
            longitude: Longitude as float
            
        Returns:
            Address string or None if not found
        """
        try:
            location = self.geolocator.reverse(f"{latitude}, {longitude}", timeout=10)
            if location:
                return location.address
            return None
        except Exception as e:
            print(f"Reverse geocoding error: {e}")
            return None
