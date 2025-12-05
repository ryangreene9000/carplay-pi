"""
Google Directions Module
Provides turn-by-turn navigation using Google Directions API
"""

import requests
import logging

logging.basicConfig(level=logging.DEBUG)

# Google Maps API Key
GOOGLE_API_KEY = "AIzaSyBa_0nyYp-MW9zWVlDsmGr9QwIuxF4Pz_Q"


def get_route_from_google(origin_lat, origin_lon, dest_lat, dest_lon):
    """
    Calls Google Directions API and returns polyline + steps.
    
    Args:
        origin_lat: Starting latitude
        origin_lon: Starting longitude
        dest_lat: Destination latitude
        dest_lon: Destination longitude
        
    Returns:
        Dictionary with polyline, distance, duration, and steps
        or None if failed
    """
    url = (
        "https://maps.googleapis.com/maps/api/directions/json?"
        f"origin={origin_lat},{origin_lon}&"
        f"destination={dest_lat},{dest_lon}&"
        "mode=driving&"
        "units=imperial&"
        f"key={GOOGLE_API_KEY}"
    )

    try:
        response = requests.get(url, timeout=15)
        data = response.json()

        if data["status"] != "OK":
            logging.error(f"Google Directions error: {data.get('status')} - {data.get('error_message', '')}")
            return None

        route = data["routes"][0]
        leg = route["legs"][0]

        # Extract step-by-step directions
        steps = []
        for step in leg["steps"]:
            # Strip HTML tags from instructions for display
            import re
            instruction = re.sub('<[^<]+?>', '', step.get("html_instructions", ""))
            
            steps.append({
                "instruction": instruction,
                "html_instruction": step.get("html_instructions", ""),
                "distance": step["distance"]["text"],
                "distance_m": step["distance"]["value"],
                "duration": step["duration"]["text"],
                "duration_s": step["duration"]["value"],
                "start_lat": step["start_location"]["lat"],
                "start_lon": step["start_location"]["lng"],
                "end_lat": step["end_location"]["lat"],
                "end_lon": step["end_location"]["lng"],
                "maneuver": step.get("maneuver", "")
            })

        result = {
            "ok": True,
            "polyline": route["overview_polyline"]["points"],
            "distance": leg["distance"]["text"],
            "distance_m": leg["distance"]["value"],
            "duration": leg["duration"]["text"],
            "duration_s": leg["duration"]["value"],
            "start_address": leg.get("start_address", ""),
            "end_address": leg.get("end_address", ""),
            "steps": steps
        }
        
        logging.debug(f"Google route: {result['distance']}, {result['duration']}, {len(steps)} steps")
        return result

    except Exception as e:
        logging.error(f"Google Directions exception: {e}")
        return None


def get_route_with_waypoints(origin, destination, waypoints=None):
    """
    Get route with optional waypoints (stops along the way).
    
    Args:
        origin: Tuple (lat, lon) or address string
        destination: Tuple (lat, lon) or address string
        waypoints: List of tuples [(lat, lon), ...] or addresses
        
    Returns:
        Dictionary with route information or None if failed
    """
    # Format origin
    if isinstance(origin, tuple):
        origin_str = f"{origin[0]},{origin[1]}"
    else:
        origin_str = origin
    
    # Format destination
    if isinstance(destination, tuple):
        dest_str = f"{destination[0]},{destination[1]}"
    else:
        dest_str = destination
    
    url = (
        "https://maps.googleapis.com/maps/api/directions/json?"
        f"origin={origin_str}&"
        f"destination={dest_str}&"
        "mode=driving&"
        "units=imperial&"
        f"key={GOOGLE_API_KEY}"
    )
    
    # Add waypoints if provided
    if waypoints:
        wp_str = "|".join(
            f"{w[0]},{w[1]}" if isinstance(w, tuple) else w
            for w in waypoints
        )
        url += f"&waypoints={wp_str}"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if data["status"] != "OK":
            logging.error(f"Google Directions error: {data}")
            return None
        
        route = data["routes"][0]
        
        # Combine all legs
        all_steps = []
        total_distance_m = 0
        total_duration_s = 0
        
        for leg in route["legs"]:
            total_distance_m += leg["distance"]["value"]
            total_duration_s += leg["duration"]["value"]
            
            for step in leg["steps"]:
                import re
                instruction = re.sub('<[^<]+?>', '', step.get("html_instructions", ""))
                
                all_steps.append({
                    "instruction": instruction,
                    "distance": step["distance"]["text"],
                    "duration": step["duration"]["text"],
                    "maneuver": step.get("maneuver", "")
                })
        
        return {
            "ok": True,
            "polyline": route["overview_polyline"]["points"],
            "distance_m": total_distance_m,
            "duration_s": total_duration_s,
            "steps": all_steps
        }
        
    except Exception as e:
        logging.error(f"Google Directions exception: {e}")
        return None

