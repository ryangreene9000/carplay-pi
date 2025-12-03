"""
Map Module
Handles map display and navigation using OpenStreetMap
Supports both coordinate input and street address geocoding
"""

import folium
import json
import os
import re
import ssl
import certifi
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


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
    
    def geocode_address(self, address):
        """
        Convert a street address to (latitude, longitude) coordinates.
        
        Args:
            address: Street address string (e.g., "123 Main St, City, State")
            
        Returns:
            Tuple of (latitude, longitude)
            
        Raises:
            ValueError: If address cannot be geocoded
        """
        try:
            location = self.geolocator.geocode(address, timeout=10)
            if location is None:
                raise ValueError(f"Could not geocode address: {address}")
            return (location.latitude, location.longitude)
        except GeocoderTimedOut:
            raise ValueError(f"Geocoding timed out for address: {address}")
        except GeocoderServiceError as e:
            raise ValueError(f"Geocoding service error: {str(e)}")
    
    def parse_location_input(self, value):
        """
        Parse user input that could be either coordinates or a street address.
        
        Args:
            value: String that is either:
                   - Coordinates like "40.78, -77.86" or "40.78,-77.86"
                   - Street address like "123 Main St, City, State"
                   
        Returns:
            Tuple of (latitude, longitude) as floats
        """
        if not value or not isinstance(value, str):
            raise ValueError("Location input cannot be empty")
        
        value = value.strip()
        
        # Check if it looks like coordinates (two numbers separated by comma)
        # Pattern: optional negative, digits, optional decimal, comma, same pattern
        coord_pattern = r'^-?\d+\.?\d*\s*,\s*-?\d+\.?\d*$'
        
        if re.match(coord_pattern, value):
            # It's coordinates - parse them
            parts = value.split(',')
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                
                # Validate coordinate ranges
                if not (-90 <= lat <= 90):
                    raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
                if not (-180 <= lon <= 180):
                    raise ValueError(f"Longitude must be between -180 and 180, got {lon}")
                    
                return (lat, lon)
            except (ValueError, IndexError) as e:
                raise ValueError(f"Invalid coordinate format: {value}")
        else:
            # It's an address - geocode it
            return self.geocode_address(value)
    
    def get_route(self, origin, destination):
        """
        Get route between two points.
        Accepts either coordinates or street addresses for both origin and destination.
        
        Args:
            origin: Starting point (coordinates string or street address)
            destination: End point (coordinates string or street address)
            
        Returns:
            Dictionary with route information or error message
        """
        try:
            # Parse origin (could be coords or address)
            origin_coords = self.parse_location_input(origin)
            
            # Parse destination (could be coords or address)
            dest_coords = self.parse_location_input(destination)
            
            # Convert to list format for compatibility
            origin_list = list(origin_coords)
            dest_list = list(dest_coords)
            
            # Calculate approximate distance (haversine formula)
            distance = self._calculate_distance(origin_coords, dest_coords)
            
            # Estimate duration (rough estimate: 30 mph average)
            duration_hours = distance / 30  # assuming 30 mph average
            duration_mins = int(duration_hours * 60)
            
            return {
                'success': True,
                'origin': origin_list,
                'origin_input': origin,
                'destination': dest_list,
                'destination_input': destination,
                'distance': f"{distance:.1f} miles",
                'duration': f"{duration_mins} mins" if duration_mins < 60 else f"{duration_hours:.1f} hours",
                'waypoints': [origin_list, dest_list]  # Simplified route
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
