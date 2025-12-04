// Map navigation JavaScript
// Supports both coordinates and street address input
// Location sources: Phone (Bluetooth) -> Pi (GPS/IP) -> Browser -> Default

let map;
let routeLayer;
let markers = [];
let currentLocation = null;
let poiMarkers = [];

// =============================================================================
// Location Services
// =============================================================================

async function getBestLocation() {
    /**
     * Get the best available location using this priority:
     * 1. Connected phone (via Bluetooth)
     * 2. Raspberry Pi (GPS or IP geolocation)
     * 3. Browser geolocation
     * 4. Default location
     */
    
    // Try backend location service (phone -> Pi)
    try {
        const response = await fetch('/api/location/current');
        const data = await response.json();
        if (data.ok && data.lat && data.lon) {
            console.log(`Location from ${data.source}: ${data.lat}, ${data.lon}`);
            return {
                lat: data.lat,
                lon: data.lon,
                source: data.source,
                city: data.city || ''
            };
        }
    } catch (e) {
        console.log('Backend location failed:', e);
    }
    
    // Fallback to browser geolocation
    if (navigator.geolocation) {
        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    timeout: 10000,
                    enableHighAccuracy: true
                });
            });
            console.log('Location from browser:', position.coords.latitude, position.coords.longitude);
            return {
                lat: position.coords.latitude,
                lon: position.coords.longitude,
                source: 'browser'
            };
        } catch (e) {
            console.log('Browser geolocation failed:', e);
        }
    }
    
    // Default location (Toronto)
    console.log('Using default location');
    return {
        lat: 43.6532,
        lon: -79.3832,
        source: 'default'
    };
}

// =============================================================================
// Map Initialization
// =============================================================================

async function initMap() {
    // Default location while we fetch actual location
    const defaultLocation = [43.6532, -79.3832];
    
    map = L.map('map').setView(defaultLocation, 13);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);
    
    // Get best available location
    const location = await getBestLocation();
    currentLocation = location;
    
    // Update map with actual location
    const userLocation = [location.lat, location.lon];
    map.setView(userLocation, 14);
    
    // Add marker for current location
    const sourceText = location.source === 'default' ? 'Default Location' : 
                       location.source === 'browser' ? 'Your Location (Browser)' :
                       location.source === 'phone' ? 'Your Location (Phone)' :
                       location.source === 'gps' ? 'Your Location (GPS)' :
                       location.source === 'ip' ? `Approximate Location (${location.city || 'IP'})` :
                       'Your Location';
    
    addMarker(userLocation, sourceText, location.source === 'default' ? 'gray' : 'blue');
    
    // Update the location info display if it exists
    const coordsDisplay = document.getElementById('current-coords');
    const locationInfo = document.getElementById('location-info');
    if (coordsDisplay) {
        coordsDisplay.textContent = `${location.lat.toFixed(6)}, ${location.lon.toFixed(6)}`;
    }
    if (locationInfo && location.source !== 'default') {
        locationInfo.style.display = 'flex';
    }
}

// =============================================================================
// Use My Location Button Handler
// =============================================================================

async function useMyLocation() {
    const locateBtn = document.getElementById('locate-btn');
    const originInput = document.getElementById('origin-input');
    const coordsDisplay = document.getElementById('current-coords');
    const locationInfo = document.getElementById('location-info');
    
    if (locateBtn) {
        locateBtn.disabled = true;
        locateBtn.innerHTML = '⏳ Finding...';
    }
    
    try {
        const location = await getBestLocation();
        currentLocation = location;
        
        // Update input field
        if (originInput) {
            originInput.value = `${location.lat.toFixed(6)}, ${location.lon.toFixed(6)}`;
        }
        
        // Update coords display
        if (coordsDisplay) {
            coordsDisplay.textContent = `${location.lat.toFixed(6)}, ${location.lon.toFixed(6)}`;
        }
        if (locationInfo) {
            locationInfo.style.display = 'flex';
        }
        
        // Center map and add marker
        const userLocation = [location.lat, location.lon];
        map.setView(userLocation, 15);
        clearMarkers();
        addMarker(userLocation, 'Your Location', 'blue');
        
        showSuccess(`Location found (${location.source})`);
        
    } catch (error) {
        console.error('Location error:', error);
        showError('Could not determine your location');
    } finally {
        if (locateBtn) {
            locateBtn.disabled = false;
            locateBtn.innerHTML = '📍 Use My Location';
        }
    }
}

// =============================================================================
// Markers
// =============================================================================

function addMarker(location, popupText, color = 'blue') {
    const colorMap = {
        'blue': '#2196F3',
        'red': '#f44336',
        'green': '#4CAF50',
        'gray': '#9E9E9E',
        'orange': '#FF9800',
        'purple': '#9C27B0'
    };
    
    const markerColor = colorMap[color] || color;
    
    const icon = L.divIcon({
        className: 'custom-marker',
        html: `<div style="
            background-color: ${markerColor};
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        "></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });
    
    const marker = L.marker(location, { icon }).addTo(map).bindPopup(popupText);
    markers.push(marker);
    return marker;
}

function addPoiMarker(location, name, type) {
    const typeIcons = {
        'fuel': '⛽',
        'gas': '⛽',
        'restaurant': '🍽️',
        'food': '🍽️',
        'parking': '🅿️',
        'hospital': '🏥',
        'pharmacy': '💊',
        'charging': '🔌'
    };
    
    const emoji = typeIcons[type] || '📍';
    
    const icon = L.divIcon({
        className: 'poi-marker',
        html: `<div style="
            background: white;
            padding: 4px 8px;
            border-radius: 15px;
            font-size: 14px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            white-space: nowrap;
        ">${emoji} ${name}</div>`,
        iconSize: null
    });
    
    const marker = L.marker(location, { icon }).addTo(map).bindPopup(`<b>${name}</b>`);
    poiMarkers.push(marker);
    return marker;
}

function clearMarkers() {
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
}

function clearPoiMarkers() {
    poiMarkers.forEach(marker => map.removeLayer(marker));
    poiMarkers = [];
}

// =============================================================================
// Places / POI Search
// =============================================================================

async function searchNearbyPlaces(placeType) {
    if (!currentLocation) {
        showError('Please get your location first');
        return;
    }
    
    clearPoiMarkers();
    
    try {
        const url = `/api/places/nearby?lat=${currentLocation.lat}&lon=${currentLocation.lon}&type=${placeType}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.ok && data.results && data.results.length > 0) {
            // Add markers for each result
            data.results.forEach(place => {
                if (place.lat && place.lon) {
                    addPoiMarker([place.lat, place.lon], place.name || 'Unknown', placeType);
                }
            });
            
            showSuccess(`Found ${data.results.length} ${placeType} nearby`);
            
            // If results exist, zoom to fit them
            if (poiMarkers.length > 0) {
                const group = new L.featureGroup(poiMarkers);
                map.fitBounds(group.getBounds().pad(0.1));
            }
        } else {
            showError(`No ${placeType} found nearby`);
        }
    } catch (error) {
        console.error('Places search error:', error);
        showError('Failed to search for places');
    }
}

// Quick destination button handler
function setDestination(place) {
    const destInput = document.getElementById('dest-input');
    if (destInput) {
        destInput.value = place + ' nearby';
    }
    
    // Also search for places if we have location
    if (currentLocation) {
        const placeType = place.toLowerCase().replace(' nearby', '').replace('gas station', 'fuel');
        searchNearbyPlaces(placeType);
    }
}

// =============================================================================
// UI Helpers
// =============================================================================

function setLoading(isLoading) {
    const routeBtn = document.getElementById('route-btn');
    if (routeBtn) {
        if (isLoading) {
            routeBtn.disabled = true;
            routeBtn.innerHTML = '⏳ Finding route...';
        } else {
            routeBtn.disabled = false;
            routeBtn.innerHTML = 'Get Directions';
        }
    }
}

function showSuccess(message) {
    let panel = document.getElementById('success-panel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'success-panel';
        panel.style.cssText = `
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 12px 20px;
            border-radius: 10px;
            margin-top: 10px;
            box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
        `;
        document.querySelector('.map-controls').appendChild(panel);
    }
    
    panel.innerHTML = `✓ ${message}`;
    panel.style.display = 'block';
    
    setTimeout(() => { panel.style.display = 'none'; }, 3000);
}

function showRouteInfo(data) {
    let infoPanel = document.getElementById('route-info-panel');
    if (!infoPanel) {
        infoPanel = document.createElement('div');
        infoPanel.id = 'route-info-panel';
        infoPanel.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-top: 15px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        `;
        document.querySelector('.map-controls').appendChild(infoPanel);
    }
    
    infoPanel.innerHTML = `
        <h4 style="margin: 0 0 10px 0; font-size: 1.1em;">🗺️ Route Found!</h4>
        <div style="display: flex; justify-content: space-between; gap: 20px;">
            <div>
                <div style="opacity: 0.8; font-size: 0.85em;">Distance</div>
                <div style="font-size: 1.2em; font-weight: 600;">${data.distance}</div>
            </div>
            <div>
                <div style="opacity: 0.8; font-size: 0.85em;">Est. Time</div>
                <div style="font-size: 1.2em; font-weight: 600;">${data.duration}</div>
            </div>
        </div>
    `;
    infoPanel.style.display = 'block';
}

function hideRouteInfo() {
    const infoPanel = document.getElementById('route-info-panel');
    if (infoPanel) {
        infoPanel.style.display = 'none';
    }
}

function showError(message) {
    let errorPanel = document.getElementById('error-panel');
    if (!errorPanel) {
        errorPanel = document.createElement('div');
        errorPanel.id = 'error-panel';
        errorPanel.style.cssText = `
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-top: 15px;
            box-shadow: 0 4px 15px rgba(235, 51, 73, 0.3);
        `;
        document.querySelector('.map-controls').appendChild(errorPanel);
    }
    
    errorPanel.innerHTML = `
        <h4 style="margin: 0 0 5px 0;">⚠️ Error</h4>
        <p style="margin: 0; opacity: 0.9;">${message}</p>
    `;
    errorPanel.style.display = 'block';
    
    setTimeout(() => { errorPanel.style.display = 'none'; }, 5000);
}

// =============================================================================
// Routing
// =============================================================================

async function calculateRoute(origin, destination) {
    setLoading(true);
    hideRouteInfo();
    
    try {
        const response = await fetch('/api/map/route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origin, destination })
        });
        const data = await response.json();
        
        if (data.success) {
            displayRoute(data);
            showRouteInfo(data);
        } else {
            showError(data.message || 'Route calculation failed');
        }
    } catch (error) {
        console.error('Error calculating route:', error);
        showError('Network error - please try again');
    } finally {
        setLoading(false);
    }
}

function displayRoute(data) {
    clearMarkers();
    clearPoiMarkers();
    if (routeLayer) {
        map.removeLayer(routeLayer);
    }
    
    const waypoints = data.waypoints;
    
    if (waypoints && waypoints.length >= 2) {
        const origin = waypoints[0];
        const destination = waypoints[waypoints.length - 1];
        
        const originLabel = data.origin_input || `${origin[0].toFixed(4)}, ${origin[1].toFixed(4)}`;
        const destLabel = data.destination_input || `${destination[0].toFixed(4)}, ${destination[1].toFixed(4)}`;
        
        const originIcon = L.divIcon({
            className: 'custom-marker',
            html: '<div style="background: #11998e; color: white; padding: 8px 12px; border-radius: 20px; font-weight: bold; white-space: nowrap; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">📍 Start</div>',
            iconSize: null
        });
        
        const destIcon = L.divIcon({
            className: 'custom-marker', 
            html: '<div style="background: #eb3349; color: white; padding: 8px 12px; border-radius: 20px; font-weight: bold; white-space: nowrap; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">🎯 End</div>',
            iconSize: null
        });
        
        L.marker(origin, {icon: originIcon}).addTo(map).bindPopup(`<b>Start:</b><br>${originLabel}`);
        L.marker(destination, {icon: destIcon}).addTo(map).bindPopup(`<b>Destination:</b><br>${destLabel}`);
        
        routeLayer = L.polyline(waypoints, {
            color: '#667eea',
            weight: 6,
            opacity: 0.8,
            dashArray: '10, 10'
        }).addTo(map);
        
        map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });
    }
}

// =============================================================================
// Event Listeners
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    
    // Route button
    const routeBtn = document.getElementById('route-btn');
    if (routeBtn) {
        routeBtn.addEventListener('click', async () => {
            const originInput = document.getElementById('origin-input');
            const destInput = document.getElementById('dest-input');
            
            const origin = originInput.value.trim();
            const destination = destInput.value.trim();
            
            if (!origin || !destination) {
                showError('Please enter both starting point and destination');
                return;
            }
            
            await calculateRoute(origin, destination);
        });
    }
    
    // Locate button
    const locateBtn = document.getElementById('locate-btn');
    if (locateBtn) {
        locateBtn.addEventListener('click', useMyLocation);
    }
});

// Make functions available globally for inline onclick handlers
window.setDestination = setDestination;
window.searchNearbyPlaces = searchNearbyPlaces;
