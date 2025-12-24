"""
Google Maps Module
Complete Google Maps integration for navigation, places, and geocoding.

SECURITY NOTE: API key is loaded from config module or environment variable.
The hardcoded API key was intentionally removed for public release.
"""

import requests
import logging
import re
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Google Maps API Key
# SECURITY: Load from config or environment variable. Hardcoded key removed.
try:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config'))
    from config import GOOGLE_MAPS_API_KEY
    GOOGLE_API_KEY = GOOGLE_MAPS_API_KEY
except ImportError:
    GOOGLE_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'PUT_API_KEY_HERE')

# =============================================================================
# Directions API - Turn-by-Turn Navigation
# =============================================================================

def get_directions(origin_lat, origin_lon, dest_lat, dest_lon, units="imperial"):
    """
    Get turn-by-turn directions from Google Directions API.
    
    Args:
        origin_lat: Starting latitude
        origin_lon: Starting longitude
        dest_lat: Destination latitude
        dest_lon: Destination longitude
        units: "imperial" (miles) or "metric" (km)
        
    Returns:
        Dictionary with route data or error
    """
    url = (
        f"https://maps.googleapis.com/maps/api/directions/json?"
        f"origin={origin_lat},{origin_lon}&"
        f"destination={dest_lat},{dest_lon}&"
        f"mode=driving&"
        f"units={units}&"
        f"key={GOOGLE_API_KEY}"
    )
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if data["status"] != "OK":
            error_msg = data.get("error_message", data["status"])
            logger.error(f"Directions API error: {error_msg}")
            return {"ok": False, "error": error_msg}
        
        route = data["routes"][0]
        leg = route["legs"][0]
        
        # Parse steps
        steps = []
        for step in leg["steps"]:
            # Strip HTML tags for clean text
            instruction = re.sub(r'<[^>]+>', '', step.get("html_instructions", ""))
            
            steps.append({
                "instruction": instruction,
                "html": step.get("html_instructions", ""),
                "distance": step["distance"]["text"],
                "distance_meters": step["distance"]["value"],
                "duration": step["duration"]["text"],
                "duration_seconds": step["duration"]["value"],
                "start_lat": step["start_location"]["lat"],
                "start_lon": step["start_location"]["lng"],
                "end_lat": step["end_location"]["lat"],
                "end_lon": step["end_location"]["lng"],
                "maneuver": step.get("maneuver", "straight"),
                "polyline": step.get("polyline", {}).get("points", "")
            })
        
        return {
            "ok": True,
            "polyline": route["overview_polyline"]["points"],
            "distance": leg["distance"]["text"],
            "distance_meters": leg["distance"]["value"],
            "duration": leg["duration"]["text"],
            "duration_seconds": leg["duration"]["value"],
            "start_address": leg.get("start_address", ""),
            "end_address": leg.get("end_address", ""),
            "steps": steps
        }
        
    except requests.exceptions.Timeout:
        logger.error("Directions API timeout")
        return {"ok": False, "error": "Request timeout"}
    except Exception as e:
        logger.error(f"Directions API exception: {e}")
        return {"ok": False, "error": str(e)}


# =============================================================================
# Places API - Nearby Search
# =============================================================================

def search_nearby(lat, lon, place_type, radius=5000):
    """
    Search for nearby places using Google Places API.
    
    Args:
        lat: Center latitude
        lon: Center longitude
        place_type: Type of place (gas_station, restaurant, parking, hospital, etc.)
        radius: Search radius in meters (default 5000 = ~3 miles)
        
    Returns:
        List of places or error
    """
    url = (
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?"
        f"location={lat},{lon}&"
        f"radius={radius}&"
        f"type={place_type}&"
        f"key={GOOGLE_API_KEY}"
    )
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if data["status"] not in ["OK", "ZERO_RESULTS"]:
            error_msg = data.get("error_message", data["status"])
            logger.error(f"Places API error: {error_msg}")
            return {"ok": False, "error": error_msg}
        
        places = []
        for place in data.get("results", []):
            loc = place["geometry"]["location"]
            places.append({
                "name": place.get("name", "Unknown"),
                "lat": loc["lat"],
                "lon": loc["lng"],
                "address": place.get("vicinity", ""),
                "rating": place.get("rating"),
                "price_level": place.get("price_level"),
                "open_now": place.get("opening_hours", {}).get("open_now"),
                "place_id": place.get("place_id"),
                "types": place.get("types", [])
            })
        
        return {"ok": True, "places": places}
        
    except requests.exceptions.Timeout:
        logger.error("Places API timeout")
        return {"ok": False, "error": "Request timeout"}
    except Exception as e:
        logger.error(f"Places API exception: {e}")
        return {"ok": False, "error": str(e)}


# =============================================================================
# Geocoding API - Address to Coordinates
# =============================================================================

def geocode(address):
    """
    Convert address to coordinates using Google Geocoding API.
    
    Args:
        address: Street address or place name
        
    Returns:
        Dictionary with lat/lon or error
    """
    from urllib.parse import quote
    encoded = quote(address)
    
    url = (
        f"https://maps.googleapis.com/maps/api/geocode/json?"
        f"address={encoded}&"
        f"key={GOOGLE_API_KEY}"
    )
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data["status"] != "OK":
            error_msg = data.get("error_message", data["status"])
            logger.error(f"Geocoding API error: {error_msg}")
            return {"ok": False, "error": error_msg}
        
        result = data["results"][0]
        loc = result["geometry"]["location"]
        
        return {
            "ok": True,
            "lat": loc["lat"],
            "lon": loc["lng"],
            "formatted_address": result.get("formatted_address", address)
        }
        
    except Exception as e:
        logger.error(f"Geocoding API exception: {e}")
        return {"ok": False, "error": str(e)}


def reverse_geocode(lat, lon):
    """
    Convert coordinates to address using Google Reverse Geocoding.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        Dictionary with address or error
    """
    url = (
        f"https://maps.googleapis.com/maps/api/geocode/json?"
        f"latlng={lat},{lon}&"
        f"key={GOOGLE_API_KEY}"
    )
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data["status"] != "OK":
            return {"ok": False, "error": data.get("error_message", data["status"])}
        
        result = data["results"][0]
        
        return {
            "ok": True,
            "address": result.get("formatted_address", "Unknown location"),
            "components": result.get("address_components", [])
        }
        
    except Exception as e:
        logger.error(f"Reverse Geocoding exception: {e}")
        return {"ok": False, "error": str(e)}


# =============================================================================
# Place Details API
# =============================================================================

def get_place_details(place_id):
    """
    Get detailed information about a place.
    
    Args:
        place_id: Google Place ID
        
    Returns:
        Dictionary with place details or error
    """
    url = (
        f"https://maps.googleapis.com/maps/api/place/details/json?"
        f"place_id={place_id}&"
        f"fields=name,formatted_address,formatted_phone_number,opening_hours,website,rating,reviews,price_level,geometry&"
        f"key={GOOGLE_API_KEY}"
    )
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data["status"] != "OK":
            return {"ok": False, "error": data.get("error_message", data["status"])}
        
        result = data.get("result", {})
        loc = result.get("geometry", {}).get("location", {})
        
        return {
            "ok": True,
            "name": result.get("name", "Unknown"),
            "address": result.get("formatted_address", ""),
            "phone": result.get("formatted_phone_number", ""),
            "website": result.get("website", ""),
            "rating": result.get("rating"),
            "price_level": result.get("price_level"),
            "lat": loc.get("lat"),
            "lon": loc.get("lng"),
            "hours": result.get("opening_hours", {}).get("weekday_text", []),
            "open_now": result.get("opening_hours", {}).get("open_now")
        }
        
    except Exception as e:
        logger.error(f"Place Details exception: {e}")
        return {"ok": False, "error": str(e)}


# =============================================================================
# Text Search API - More flexible search
# =============================================================================

def search_text(query, lat=None, lon=None, radius=5000):
    """
    Search for places using text query.
    
    Args:
        query: Search text (e.g., "pizza near me", "Walmart", "gas station")
        lat: Optional center latitude for location bias
        lon: Optional center longitude for location bias
        radius: Search radius in meters
        
    Returns:
        List of places or error
    """
    from urllib.parse import quote
    encoded = quote(query)
    
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={encoded}&key={GOOGLE_API_KEY}"
    
    if lat and lon:
        url += f"&location={lat},{lon}&radius={radius}"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if data["status"] not in ["OK", "ZERO_RESULTS"]:
            return {"ok": False, "error": data.get("error_message", data["status"])}
        
        places = []
        for place in data.get("results", []):
            loc = place["geometry"]["location"]
            places.append({
                "name": place.get("name", "Unknown"),
                "lat": loc["lat"],
                "lon": loc["lng"],
                "address": place.get("formatted_address", ""),
                "rating": place.get("rating"),
                "place_id": place.get("place_id"),
                "types": place.get("types", [])
            })
        
        return {"ok": True, "places": places}
        
    except Exception as e:
        logger.error(f"Text Search exception: {e}")
        return {"ok": False, "error": str(e)}


# =============================================================================
# Polyline Decoder (for use by frontend or backend)
# =============================================================================

def decode_polyline(encoded):
    """
    Decode Google's encoded polyline format.
    
    Args:
        encoded: Encoded polyline string
        
    Returns:
        List of [lat, lon] coordinate pairs
    """
    points = []
    index = 0
    length = len(encoded)
    lat = 0
    lng = 0
    
    while index < length:
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
        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat
        
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
        dlng = ~(result >> 1) if result & 1 else result >> 1
        lng += dlng
        
        points.append([lat / 1e5, lng / 1e5])
    
    return points


# =============================================================================
# Convenience Functions
# =============================================================================

def route_to_address(origin_lat, origin_lon, destination_address):
    """
    Get directions from coordinates to an address.
    """
    geo = geocode(destination_address)
    if not geo["ok"]:
        return geo
    
    return get_directions(origin_lat, origin_lon, geo["lat"], geo["lon"])


def find_nearest(lat, lon, place_type):
    """
    Find the single nearest place of a type.
    """
    result = search_nearby(lat, lon, place_type, radius=10000)
    if not result["ok"] or not result["places"]:
        return {"ok": False, "error": "No places found"}
    
    return {"ok": True, "place": result["places"][0]}

