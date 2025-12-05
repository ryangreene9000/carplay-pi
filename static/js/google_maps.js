/**
 * Google Maps Navigation Module
 * Clean frontend integration for turn-by-turn navigation
 */

// =============================================================================
// Polyline Decoder
// =============================================================================

function decodeGooglePolyline(encoded) {
    const points = [];
    let index = 0;
    const len = encoded.length;
    let lat = 0;
    let lng = 0;

    while (index < len) {
        let b, shift = 0, result = 0;
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        const dlat = (result & 1) ? ~(result >> 1) : (result >> 1);
        lat += dlat;

        shift = 0;
        result = 0;
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        const dlng = (result & 1) ? ~(result >> 1) : (result >> 1);
        lng += dlng;

        points.push([lat / 1e5, lng / 1e5]);
    }

    return points;
}

// =============================================================================
// API Calls
// =============================================================================

async function getGoogleRoute(originLat, originLon, destLat, destLon) {
    /**
     * Get turn-by-turn route from backend Google Maps API
     */
    const url = `/api/google/directions?olat=${originLat}&olon=${originLon}&dlat=${destLat}&dlon=${destLon}`;
    
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error('Google route error:', error);
        return { ok: false, error: 'Network error' };
    }
}

async function searchGooglePlaces(lat, lon, type, radius = 5000) {
    /**
     * Search for nearby places via backend
     */
    const url = `/api/google/places?lat=${lat}&lon=${lon}&type=${type}&radius=${radius}`;
    
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error('Google places error:', error);
        return { ok: false, error: 'Network error' };
    }
}

async function geocodeAddress(address) {
    /**
     * Convert address to coordinates
     */
    const url = `/api/google/geocode?address=${encodeURIComponent(address)}`;
    
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error('Geocode error:', error);
        return { ok: false, error: 'Network error' };
    }
}

async function searchGoogleText(query, lat = null, lon = null) {
    /**
     * Text-based place search
     */
    let url = `/api/google/search?q=${encodeURIComponent(query)}`;
    if (lat && lon) {
        url += `&lat=${lat}&lon=${lon}`;
    }
    
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error('Search error:', error);
        return { ok: false, error: 'Network error' };
    }
}

// =============================================================================
// Map Drawing Functions (requires Leaflet map instance)
// =============================================================================

let googleRouteLine = null;
let googleMarkers = [];

function clearGoogleRoute(map) {
    /**
     * Remove existing route from map
     */
    if (googleRouteLine) {
        map.removeLayer(googleRouteLine);
        googleRouteLine = null;
    }
    
    googleMarkers.forEach(marker => {
        map.removeLayer(marker);
    });
    googleMarkers = [];
}

function drawGoogleRoute(map, routeData, options = {}) {
    /**
     * Draw route on Leaflet map
     * 
     * Args:
     *   map: Leaflet map instance
     *   routeData: Response from getGoogleRoute()
     *   options: { color, weight, showMarkers, fitBounds }
     */
    if (!routeData.ok || !routeData.polyline) {
        console.error('Invalid route data');
        return false;
    }
    
    const {
        color = '#4285F4',
        weight = 6,
        showMarkers = true,
        fitBounds = true
    } = options;
    
    // Clear existing
    clearGoogleRoute(map);
    
    // Decode polyline
    const latlngs = decodeGooglePolyline(routeData.polyline);
    
    // Draw route line
    googleRouteLine = L.polyline(latlngs, {
        color: color,
        weight: weight,
        opacity: 0.9,
        lineJoin: 'round'
    }).addTo(map);
    
    if (showMarkers) {
        // Start marker
        const startIcon = L.divIcon({
            className: 'gm-marker',
            html: `<div style="
                background: #34A853;
                color: white;
                padding: 6px 10px;
                border-radius: 16px;
                font-weight: bold;
                font-size: 11px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            ">START</div>`,
            iconSize: null
        });
        const startMarker = L.marker(latlngs[0], { icon: startIcon }).addTo(map);
        if (routeData.start_address) {
            startMarker.bindPopup(routeData.start_address);
        }
        googleMarkers.push(startMarker);
        
        // End marker
        const endIcon = L.divIcon({
            className: 'gm-marker',
            html: `<div style="
                background: #EA4335;
                color: white;
                padding: 6px 10px;
                border-radius: 16px;
                font-weight: bold;
                font-size: 11px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            ">END</div>`,
            iconSize: null
        });
        const endMarker = L.marker(latlngs[latlngs.length - 1], { icon: endIcon }).addTo(map);
        if (routeData.end_address) {
            endMarker.bindPopup(routeData.end_address);
        }
        googleMarkers.push(endMarker);
    }
    
    if (fitBounds) {
        map.fitBounds(googleRouteLine.getBounds(), { padding: [40, 40] });
    }
    
    return true;
}

// =============================================================================
// Turn-by-Turn UI
// =============================================================================

function createTurnPanel(containerId = 'googleTurnPanel') {
    /**
     * Create turn-by-turn panel HTML if it doesn't exist
     */
    let panel = document.getElementById(containerId);
    if (!panel) {
        panel = document.createElement('div');
        panel.id = containerId;
        panel.className = 'google-turn-panel';
        panel.style.cssText = `
            position: absolute;
            bottom: 10px;
            left: 10px;
            right: 10px;
            max-height: 200px;
            overflow-y: auto;
            background: rgba(20, 20, 25, 0.95);
            color: white;
            border-radius: 12px;
            z-index: 1002;
            display: none;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        `;
        document.body.appendChild(panel);
    }
    return panel;
}

function showTurnByTurn(routeData, containerId = 'googleTurnPanel') {
    /**
     * Display turn-by-turn directions
     */
    const panel = createTurnPanel(containerId);
    
    if (!routeData.ok || !routeData.steps) {
        panel.style.display = 'none';
        return;
    }
    
    const maneuverIcons = {
        'turn-left': '[L]',
        'turn-right': '[R]',
        'turn-slight-left': '[sl]',
        'turn-slight-right': '[sr]',
        'turn-sharp-left': '[HL]',
        'turn-sharp-right': '[HR]',
        'uturn-left': '[U]',
        'uturn-right': '[U]',
        'keep-left': '[kl]',
        'keep-right': '[kr]',
        'merge': '[M]',
        'ramp-left': '[rl]',
        'ramp-right': '[rr]',
        'fork-left': '[fl]',
        'fork-right': '[fr]',
        'roundabout-left': '[O]',
        'roundabout-right': '[O]',
        'straight': '[^]',
        '': '[^]'
    };
    
    const stepsHtml = routeData.steps.map((step, i) => {
        const icon = maneuverIcons[step.maneuver] || '[^]';
        return `
            <div style="display: flex; align-items: center; gap: 10px; padding: 8px 12px; 
                        background: rgba(255,255,255,0.08); border-radius: 8px; margin-bottom: 6px;
                        cursor: pointer;" 
                 onclick="if(window.googleMap) window.googleMap.setView([${step.start_lat}, ${step.start_lon}], 17)">
                <span style="background: #4285F4; color: white; padding: 4px 8px; border-radius: 4px; 
                             font-weight: bold; font-size: 11px; min-width: 28px; text-align: center;">${icon}</span>
                <span style="flex: 1; font-size: 13px;">${step.instruction}</span>
                <span style="color: rgba(255,255,255,0.6); font-size: 11px;">${step.distance}</span>
            </div>
        `;
    }).join('');
    
    panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; 
                    padding: 10px 15px; background: linear-gradient(135deg, #4285F4, #1a73e8); 
                    border-radius: 12px 12px 0 0;">
            <div><strong>${routeData.distance}</strong> - <strong>${routeData.duration}</strong></div>
            <button onclick="document.getElementById('${containerId}').style.display='none'; 
                            if(window.clearGoogleRoute && window.googleMap) clearGoogleRoute(window.googleMap);"
                    style="background: rgba(255,255,255,0.2); border: none; color: white; 
                           padding: 5px 10px; border-radius: 6px; cursor: pointer; font-weight: bold;">[X]</button>
        </div>
        <div style="padding: 10px; max-height: 150px; overflow-y: auto;">
            ${stepsHtml}
        </div>
    `;
    
    panel.style.display = 'block';
}

function hideTurnByTurn(containerId = 'googleTurnPanel') {
    const panel = document.getElementById(containerId);
    if (panel) {
        panel.style.display = 'none';
    }
}

// =============================================================================
// High-Level Navigation Function
// =============================================================================

async function navigateWithGoogle(map, originLat, originLon, destLat, destLon, options = {}) {
    /**
     * Complete navigation: get route, draw on map, show directions
     * 
     * Args:
     *   map: Leaflet map instance
     *   originLat, originLon: Starting point
     *   destLat, destLon: Destination
     *   options: { showTurnPanel, onSuccess, onError }
     */
    const { showTurnPanel = true, onSuccess, onError } = options;
    
    // Store map reference for click handlers
    window.googleMap = map;
    
    // Get route
    const route = await getGoogleRoute(originLat, originLon, destLat, destLon);
    
    if (!route.ok) {
        if (onError) onError(route.error || 'Route failed');
        return null;
    }
    
    // Draw on map
    drawGoogleRoute(map, route);
    
    // Show turn-by-turn
    if (showTurnPanel) {
        showTurnByTurn(route);
    }
    
    if (onSuccess) onSuccess(route);
    
    return route;
}

// =============================================================================
// Export for global use
// =============================================================================

window.GoogleMaps = {
    // API
    getRoute: getGoogleRoute,
    searchPlaces: searchGooglePlaces,
    geocode: geocodeAddress,
    searchText: searchGoogleText,
    
    // Polyline
    decodePolyline: decodeGooglePolyline,
    
    // Map drawing
    drawRoute: drawGoogleRoute,
    clearRoute: clearGoogleRoute,
    
    // Turn-by-turn
    showTurnByTurn: showTurnByTurn,
    hideTurnByTurn: hideTurnByTurn,
    
    // High-level
    navigate: navigateWithGoogle
};

// Also export individual functions
window.getGoogleRoute = getGoogleRoute;
window.searchGooglePlaces = searchGooglePlaces;
window.geocodeAddress = geocodeAddress;
window.decodeGooglePolyline = decodeGooglePolyline;
window.drawGoogleRoute = drawGoogleRoute;
window.clearGoogleRoute = clearGoogleRoute;
window.navigateWithGoogle = navigateWithGoogle;

