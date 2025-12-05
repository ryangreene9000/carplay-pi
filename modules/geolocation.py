"""
Google Geolocation Module
WiFi-based accurate location using Google Geolocation API
Works on Raspberry Pi by scanning nearby WiFi networks
"""

import subprocess
import re
import requests
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Google API Key
GOOGLE_API_KEY = "AIzaSyBa_0nyYp-MW9zWVlDsmGr9QwIuxF4Pz_Q"
GEOLOCATION_URL = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"


def frequency_to_channel(freq_mhz):
    """
    Convert WiFi frequency (MHz) to channel number.
    
    2.4 GHz band: channels 1-14
    5 GHz band: channels 36-165
    """
    freq = int(freq_mhz)
    
    # 2.4 GHz band (2412 - 2484 MHz)
    if 2412 <= freq <= 2484:
        if freq == 2484:
            return 14  # Japan only
        return (freq - 2412) // 5 + 1
    
    # 5 GHz band
    if 5170 <= freq <= 5825:
        # Common 5GHz channels
        channel_map = {
            5180: 36, 5200: 40, 5220: 44, 5240: 48,
            5260: 52, 5280: 56, 5300: 60, 5320: 64,
            5500: 100, 5520: 104, 5540: 108, 5560: 112,
            5580: 116, 5600: 120, 5620: 124, 5640: 128,
            5660: 132, 5680: 136, 5700: 140, 5720: 144,
            5745: 149, 5765: 153, 5785: 157, 5805: 161, 5825: 165
        }
        if freq in channel_map:
            return channel_map[freq]
        # Approximate calculation
        return (freq - 5000) // 5
    
    return None


def scan_wifi_networks():
    """
    Scan for nearby WiFi networks using iw command.
    Returns list of access points with BSSID, signal strength, and channel.
    
    Requires: sudo privileges or cap_net_admin capability
    """
    access_points = {}
    
    # Try different scan commands
    scan_commands = [
        ["sudo", "iw", "dev", "wlan0", "scan"],
        ["iw", "dev", "wlan0", "scan"],
        ["sudo", "iwlist", "wlan0", "scan"],
        ["iwlist", "wlan0", "scan"]
    ]
    
    scan_output = None
    used_command = None
    
    for cmd in scan_commands:
        try:
            logger.debug(f"Trying WiFi scan command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout:
                scan_output = result.stdout
                used_command = cmd[0]
                logger.debug(f"WiFi scan successful with: {' '.join(cmd)}")
                break
            else:
                logger.debug(f"Command failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out: {' '.join(cmd)}")
        except FileNotFoundError:
            logger.debug(f"Command not found: {cmd[0]}")
        except Exception as e:
            logger.debug(f"Command error: {e}")
    
    if not scan_output:
        logger.error("All WiFi scan methods failed")
        return []
    
    # Parse based on command used
    if "iw" in used_command:
        access_points = parse_iw_scan(scan_output)
    else:
        access_points = parse_iwlist_scan(scan_output)
    
    # Convert to list and sort by signal strength
    ap_list = list(access_points.values())
    ap_list.sort(key=lambda x: x.get('signalStrength', -100), reverse=True)
    
    logger.info(f"Found {len(ap_list)} unique WiFi networks")
    return ap_list


def parse_iw_scan(output):
    """Parse output from 'iw dev wlan0 scan'"""
    access_points = {}
    current_bssid = None
    current_ap = {}
    
    for line in output.split('\n'):
        line = line.strip()
        
        # New BSS (access point)
        bss_match = re.match(r'BSS ([0-9a-fA-F:]{17})', line)
        if bss_match:
            # Save previous AP
            if current_bssid and current_ap.get('macAddress'):
                if current_bssid not in access_points or \
                   current_ap.get('signalStrength', -100) > access_points[current_bssid].get('signalStrength', -100):
                    access_points[current_bssid] = current_ap
            
            current_bssid = bss_match.group(1).lower()
            current_ap = {'macAddress': current_bssid}
            continue
        
        # Signal strength
        signal_match = re.match(r'signal:\s*(-?\d+(?:\.\d+)?)\s*dBm', line)
        if signal_match:
            current_ap['signalStrength'] = int(float(signal_match.group(1)))
            continue
        
        # Frequency
        freq_match = re.match(r'freq:\s*(\d+)', line)
        if freq_match:
            freq = int(freq_match.group(1))
            channel = frequency_to_channel(freq)
            if channel:
                current_ap['channel'] = channel
            continue
    
    # Don't forget the last AP
    if current_bssid and current_ap.get('macAddress'):
        if current_bssid not in access_points or \
           current_ap.get('signalStrength', -100) > access_points[current_bssid].get('signalStrength', -100):
            access_points[current_bssid] = current_ap
    
    return access_points


def parse_iwlist_scan(output):
    """Parse output from 'iwlist wlan0 scan'"""
    access_points = {}
    current_bssid = None
    current_ap = {}
    
    for line in output.split('\n'):
        line = line.strip()
        
        # Cell (access point)
        cell_match = re.search(r'Address:\s*([0-9a-fA-F:]{17})', line)
        if cell_match:
            # Save previous AP
            if current_bssid and current_ap.get('macAddress'):
                if current_bssid not in access_points or \
                   current_ap.get('signalStrength', -100) > access_points[current_bssid].get('signalStrength', -100):
                    access_points[current_bssid] = current_ap
            
            current_bssid = cell_match.group(1).lower()
            current_ap = {'macAddress': current_bssid}
            continue
        
        # Signal level
        signal_match = re.search(r'Signal level[=:]?\s*(-?\d+)', line)
        if signal_match:
            current_ap['signalStrength'] = int(signal_match.group(1))
            continue
        
        # Channel
        channel_match = re.search(r'Channel[=:]?\s*(\d+)', line)
        if channel_match:
            current_ap['channel'] = int(channel_match.group(1))
            continue
        
        # Frequency (backup)
        freq_match = re.search(r'Frequency[=:]?\s*([\d.]+)\s*GHz', line)
        if freq_match and 'channel' not in current_ap:
            freq_ghz = float(freq_match.group(1))
            freq_mhz = int(freq_ghz * 1000)
            channel = frequency_to_channel(freq_mhz)
            if channel:
                current_ap['channel'] = channel
            continue
    
    # Don't forget the last AP
    if current_bssid and current_ap.get('macAddress'):
        if current_bssid not in access_points or \
           current_ap.get('signalStrength', -100) > access_points[current_bssid].get('signalStrength', -100):
            access_points[current_bssid] = current_ap
    
    return access_points


def get_accurate_location():
    """
    Get accurate location using Google Geolocation API with WiFi data.
    
    Returns:
        dict: {ok: True, lat: float, lon: float, accuracy: float, source: str}
              or {ok: False, error: str}
    """
    # Step 1: Scan WiFi networks
    wifi_networks = scan_wifi_networks()
    
    if not wifi_networks:
        logger.warning("No WiFi networks found, cannot use WiFi geolocation")
        return {
            "ok": False,
            "error": "No WiFi networks found",
            "source": "wifi_scan_failed"
        }
    
    # Step 2: Build request for Google Geolocation API
    # Filter to APs with required fields
    valid_aps = [
        ap for ap in wifi_networks
        if ap.get('macAddress') and ap.get('signalStrength')
    ]
    
    if len(valid_aps) < 2:
        logger.warning(f"Only {len(valid_aps)} valid APs, need at least 2 for accurate location")
        return {
            "ok": False,
            "error": "Not enough WiFi networks for accurate location",
            "source": "insufficient_aps"
        }
    
    # Take top 20 strongest signals
    valid_aps = valid_aps[:20]
    
    request_body = {
        "considerIp": False,
        "wifiAccessPoints": valid_aps
    }
    
    logger.debug(f"Google Geolocation request with {len(valid_aps)} APs")
    logger.debug(f"Sample AP: {valid_aps[0] if valid_aps else 'none'}")
    
    # Step 3: Call Google Geolocation API
    try:
        response = requests.post(
            GEOLOCATION_URL,
            json=request_body,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        data = response.json()
        
        if response.status_code != 200:
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            logger.error(f"Google Geolocation API error: {error_msg}")
            logger.error(f"Response: {data}")
            return {
                "ok": False,
                "error": error_msg,
                "source": "google_api_error"
            }
        
        location = data.get('location', {})
        accuracy = data.get('accuracy', 0)
        
        result = {
            "ok": True,
            "lat": location.get('lat'),
            "lon": location.get('lng'),
            "accuracy": accuracy,
            "source": "google_wifi",
            "wifi_count": len(valid_aps)
        }
        
        logger.info(f"Google Geolocation success: {result['lat']}, {result['lon']} (±{accuracy}m)")
        return result
        
    except requests.exceptions.Timeout:
        logger.error("Google Geolocation API timeout")
        return {"ok": False, "error": "API timeout", "source": "timeout"}
    except Exception as e:
        logger.error(f"Google Geolocation exception: {e}")
        return {"ok": False, "error": str(e), "source": "exception"}


def get_location_with_fallback():
    """
    Try to get location using WiFi first, then fall back to IP geolocation.
    
    Returns:
        dict: Location with lat, lon, accuracy, and source
    """
    # Try WiFi-based location first
    wifi_result = get_accurate_location()
    
    if wifi_result.get('ok'):
        return wifi_result
    
    logger.info(f"WiFi location failed ({wifi_result.get('error')}), trying IP fallback")
    
    # Fallback to IP-based location
    try:
        # Try ipinfo.io
        response = requests.get("https://ipinfo.io/json", timeout=5)
        if response.status_code == 200:
            data = response.json()
            loc = data.get('loc', '').split(',')
            if len(loc) == 2:
                return {
                    "ok": True,
                    "lat": float(loc[0]),
                    "lon": float(loc[1]),
                    "accuracy": 5000,  # IP location is ~5km accurate
                    "source": "ip_fallback",
                    "city": data.get('city', ''),
                    "region": data.get('region', '')
                }
    except Exception as e:
        logger.error(f"IP fallback error: {e}")
    
    # Final fallback - Google with IP consideration
    try:
        response = requests.post(
            GEOLOCATION_URL,
            json={"considerIp": True},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            location = data.get('location', {})
            return {
                "ok": True,
                "lat": location.get('lat'),
                "lon": location.get('lng'),
                "accuracy": data.get('accuracy', 10000),
                "source": "google_ip_fallback"
            }
    except Exception as e:
        logger.error(f"Google IP fallback error: {e}")
    
    return {
        "ok": False,
        "error": "All location methods failed",
        "source": "all_failed"
    }


# For testing
if __name__ == "__main__":
    print("Testing WiFi scan...")
    networks = scan_wifi_networks()
    print(f"Found {len(networks)} networks:")
    for ap in networks[:5]:
        print(f"  {ap}")
    
    print("\nTesting accurate location...")
    location = get_location_with_fallback()
    print(f"Result: {location}")

