"""
Configuration for Car Stereo System
Store API keys and other settings here
"""

import os

# Google Maps API Key
# Used for: Geocoding, Directions, Places API
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'AIzaSyBa_0nyYp-MW9zWVlDsmGr9QwIuxF4Pz_Q')

# Default location (used when no GPS available)
DEFAULT_LOCATION = {
    'lat': 43.6532,
    'lon': -79.3832,
    'city': 'Toronto'
}

# Map settings
MAP_SETTINGS = {
    'default_zoom': 13,
    'navigation_zoom': 16,
    'poi_search_radius': 8000  # meters
}

# Feature flags
USE_GOOGLE_MAPS = True  # Use Google Maps API when available
USE_OSRM_FALLBACK = True  # Fall back to OSRM if Google fails

