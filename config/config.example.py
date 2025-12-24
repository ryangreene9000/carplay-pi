"""
Configuration Example for Car Stereo System
Copy this file to config.py and fill in your API keys.

SECURITY: Never commit config.py to version control.
This file (config.example.py) is safe to commit as it contains no secrets.
"""

import os

# Google Maps API Key
# Get your API key from: https://console.cloud.google.com/google/maps-apis
# Required APIs: Maps JavaScript API, Directions API, Places API, Geocoding API
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'PUT_API_KEY_HERE')

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

