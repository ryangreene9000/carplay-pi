// Map navigation JavaScript
// Supports coordinates, street addresses, POI navigation, and turn-by-turn directions
// Location sources: Phone (Bluetooth) -> Pi (GPS/IP) -> Browser -> Default

let map;
let routeLayer;
let currentRouteLayer = null;
let markers = [];
let poiMarkers = [];
let selectedPlace = null;

// Store current location globally for navigation
window.currentLocation = null;

// Current location marker (for real-time updates)
let currentLocationMarker = null;
let locationPollingInterval = null;
let isNavigating = false;  // Track if actively navigating

// Touch zoom tracking for Raspberry Pi fix
let lastPinchDistance = null;

// Google route line
window.routeLine = null;

// =============================================================================
// Google Polyline Decoder
// =============================================================================

function decodePolyline(encoded) {
    /**
     * Decode Google's encoded polyline format into lat/lon coordinates.
     * This is the standard Google polyline encoding algorithm.
     */
    let points = [];
    let index = 0, len = encoded.length;
    let lat = 0, lng = 0;

    while (index < len) {
        let b, shift = 0, result = 0;
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        let dlat = (result & 1) ? ~(result >> 1) : (result >> 1);
        lat += dlat;

        shift = 0;
        result = 0;
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        let dlng = (result & 1) ? ~(result >> 1) : (result >> 1);
        lng += dlng;

        points.push({ lat: lat / 1e5, lon: lng / 1e5 });
    }

    return points;
}

// =============================================================================
// Google Navigation Functions
// =============================================================================

async function fetchGoogleRoute(origin, dest) {
    /**
     * Fetch turn-by-turn route from Google Directions API.
     * 
     * Args:
     *   origin: {lat, lon} object
     *   dest: {lat, lon} object
     *   
     * Returns:
     *   Route object with polyline, distance, duration, and steps
     */
    const url = `/api/navigation/route?olat=${origin.lat}&olon=${origin.lon}&dlat=${dest.lat}&dlon=${dest.lon}`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Route fetch error:', error);
        return { ok: false, error: 'Network error' };
    }
}

async function showGoogleRouteOnMap(origin, dest) {
    /**
     * Get Google route and display it on the map with turn-by-turn directions.
     */
    showSuccess('Getting route from Google...');
    
    const route = await fetchGoogleRoute(origin, dest);
    
    if (!route.ok || route.error) {
        showError(route.error || 'Route lookup failed');
        return;
    }
    
    // Mark as navigating
    isNavigating = true;
    
    // Clear any existing route
    if (window.routeLine) {
        map.removeLayer(window.routeLine);
        window.routeLine = null;
    }
    
    if (currentRouteLayer) {
        map.removeLayer(currentRouteLayer);
        currentRouteLayer = null;
    }
    
    clearMarkers();
    clearPoiMarkers();
    
    // Decode the polyline
    const points = decodePolyline(route.polyline);
    const latlngs = points.map(p => [p.lat, p.lon]);
    
    // Draw the route line
    window.routeLine = L.polyline(latlngs, {
        color: '#4285F4',  // Google blue
        weight: 6,
        opacity: 0.9,
        lineJoin: 'round'
    }).addTo(map);
    
    // Add start marker
    const startIcon = L.divIcon({
        className: 'route-marker',
        html: `<div style="
            background: linear-gradient(135deg, #34A853 0%, #0F9D58 100%);
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 12px;
            white-space: nowrap;
            box-shadow: 0 3px 10px rgba(52, 168, 83, 0.4);
        ">START</div>`,
        iconSize: null
    });
    L.marker(latlngs[0], {icon: startIcon}).addTo(map).bindPopup(route.start_address || 'Starting point');
    
    // Add end marker
    const endIcon = L.divIcon({
        className: 'route-marker',
        html: `<div style="
            background: linear-gradient(135deg, #EA4335 0%, #C5221F 100%);
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 12px;
            white-space: nowrap;
            box-shadow: 0 3px 10px rgba(234, 67, 53, 0.4);
        ">DEST</div>`,
        iconSize: null
    });
    L.marker(latlngs[latlngs.length - 1], {icon: endIcon}).addTo(map).bindPopup(route.end_address || 'Destination');
    
    // Fit map to show entire route
    map.fitBounds(window.routeLine.getBounds(), { padding: [50, 50] });
    
    // Show turn-by-turn panel
    updateTurnByTurnPanel(route.steps, route.distance, route.duration);
    
    showSuccess(`Route: ${route.distance} - ${route.duration}`);
}

function updateTurnByTurnPanel(steps, distance, duration) {
    /**
     * Update the turn-by-turn directions panel.
     */
    const panel = document.getElementById('turnList');
    if (!panel) return;
    
    // Show the panel
    panel.style.display = 'block';
    
    // Build step HTML
    const stepsHtml = steps.map((step, index) => {
        const maneuverIcon = getManeuverIconForGoogle(step.maneuver);
        return `
            <div class="turn-step" onclick="focusStepOnMap(${index}, ${step.start_lat}, ${step.start_lon})">
                <span class="turn-icon">${maneuverIcon}</span>
                <span class="turn-text">${step.instruction}</span>
                <span class="turn-dist">${step.distance}</span>
            </div>
        `;
    }).join('');
    
    panel.innerHTML = `
        <div class="turn-header">
            <div class="turn-summary">
                <strong>${distance}</strong> - <strong>${duration}</strong>
            </div>
            <button class="turn-close" onclick="closeTurnPanel()">[X]</button>
        </div>
        <div class="turn-steps">
            ${stepsHtml}
        </div>
    `;
}

function getManeuverIconForGoogle(maneuver) {
    /**
     * Get text icon for Google maneuver type.
     */
    const icons = {
        'turn-left': '[L]',
        'turn-right': '[R]',
        'turn-slight-left': '[SL]',
        'turn-slight-right': '[SR]',
        'turn-sharp-left': '[HL]',
        'turn-sharp-right': '[HR]',
        'uturn-left': '[U]',
        'uturn-right': '[U]',
        'keep-left': '[KL]',
        'keep-right': '[KR]',
        'merge': '[M]',
        'ramp-left': '[RL]',
        'ramp-right': '[RR]',
        'fork-left': '[FL]',
        'fork-right': '[FR]',
        'roundabout-left': '[O]',
        'roundabout-right': '[O]',
        'straight': '[^]',
        '': '[^]'
    };
    return icons[maneuver] || '[^]';
}

function focusStepOnMap(index, lat, lon) {
    /**
     * Center map on a specific turn step.
     */
    if (lat && lon) {
        map.setView([lat, lon], 17);
    }
}

function closeTurnPanel() {
    /**
     * Close the turn-by-turn panel and clear route.
     */
    const panel = document.getElementById('turnList');
    if (panel) {
        panel.style.display = 'none';
    }
    
    // Clear route line
    if (window.routeLine) {
        map.removeLayer(window.routeLine);
        window.routeLine = null;
    }
    
    clearMarkers();
    isNavigating = false;
    
    // Recenter on current location
    if (window.currentLocation) {
        map.setView([window.currentLocation.lat, window.currentLocation.lon], 14);
    }
}

// Make functions globally available
window.showGoogleRouteOnMap = showGoogleRouteOnMap;
window.closeTurnPanel = closeTurnPanel;
window.focusStepOnMap = focusStepOnMap;

// =============================================================================
// Touch Zoom Fix for Raspberry Pi
// =============================================================================

function setupTouchZoomFix() {
    /**
     * Fix for Raspberry Pi touchscreen where pinch-to-zoom only works in one direction.
     * This is a known Chromium + RPi touchscreen issue with multi-touch events.
     */
    
    const mapElement = document.getElementById('map');
    if (!mapElement) return;
    
    // Ensure touch zoom is enabled
    if (map.touchZoom) {
        map.touchZoom.enable();
    }
    
    // Manual pinch-zoom fallback that handles both zoom in AND zoom out
    let initialDistance = null;
    let initialZoom = null;
    let isZooming = false;
    
    mapElement.addEventListener('touchstart', function(e) {
        if (e.touches.length === 2) {
            // Two fingers down - start zoom gesture
            const p1 = e.touches[0];
            const p2 = e.touches[1];
            
            const dx = p1.pageX - p2.pageX;
            const dy = p1.pageY - p2.pageY;
            
            initialDistance = Math.sqrt(dx * dx + dy * dy);
            initialZoom = map.getZoom();
            isZooming = true;
            lastPinchDistance = initialDistance;
            
            // Prevent default to avoid conflicts
            e.preventDefault();
        }
    }, { passive: false });
    
    mapElement.addEventListener('touchmove', function(e) {
        if (e.touches.length === 2 && isZooming && initialDistance !== null) {
            const p1 = e.touches[0];
            const p2 = e.touches[1];
            
            const dx = p1.pageX - p2.pageX;
            const dy = p1.pageY - p2.pageY;
            
            const currentDistance = Math.sqrt(dx * dx + dy * dy);
            
            // Calculate zoom delta based on pinch scale
            const scale = currentDistance / initialDistance;
            const zoomDelta = Math.log2(scale);
            
            // Apply zoom with bounds checking
            const newZoom = initialZoom + zoomDelta;
            const clampedZoom = Math.max(map.getMinZoom(), Math.min(map.getMaxZoom(), newZoom));
            
            // Calculate center point between fingers
            const centerX = (p1.pageX + p2.pageX) / 2;
            const centerY = (p1.pageY + p2.pageY) / 2;
            
            // Get the map container's position
            const rect = mapElement.getBoundingClientRect();
            const containerPoint = L.point(centerX - rect.left, centerY - rect.top);
            const latlng = map.containerPointToLatLng(containerPoint);
            
            // Set zoom around the pinch center
            map.setZoomAround(latlng, clampedZoom, { animate: false });
            
            // Prevent default to avoid conflicts
            e.preventDefault();
        }
    }, { passive: false });
    
    mapElement.addEventListener('touchend', function(e) {
        if (e.touches.length < 2) {
            // Reset when fingers are lifted
            initialDistance = null;
            initialZoom = null;
            isZooming = false;
            lastPinchDistance = null;
        }
    });
    
    mapElement.addEventListener('touchcancel', function(e) {
        // Reset on touch cancel
        initialDistance = null;
        initialZoom = null;
        isZooming = false;
        lastPinchDistance = null;
    });
    
    console.log('Touch zoom fix initialized for Raspberry Pi');
}

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
// Real-Time Location Updates (iPhone GPS Bridge)
// =============================================================================

function setCurrentLocation(lat, lon, source = 'phone') {
    /**
     * Update the current location and optionally move the marker.
     * Called by real-time polling from iPhone GPS bridge.
     */
    window.currentLocation = { lat, lon, source };
    
    // Update the location marker on the map
    if (map) {
        const location = [lat, lon];
        
        // Create or update the current location marker
        if (currentLocationMarker) {
            currentLocationMarker.setLatLng(location);
        } else {
            // Create a distinctive "current location" marker
            const icon = L.divIcon({
                className: 'current-location-marker',
                html: `<div style="
                    width: 18px;
                    height: 18px;
                    background: #4285F4;
                    border: 3px solid white;
                    border-radius: 50%;
                    box-shadow: 0 0 10px rgba(66, 133, 244, 0.5), 0 2px 5px rgba(0,0,0,0.3);
                "></div>`,
                iconSize: [18, 18],
                iconAnchor: [9, 9]
            });
            
            currentLocationMarker = L.marker(location, { icon, zIndexOffset: 1000 })
                .addTo(map)
                .bindPopup(`Your Location (${source})`);
        }
        
        // Only auto-center if not actively navigating and not in POI search
        const placesPanel = document.getElementById('places-panel');
        const directionsPanel = document.getElementById('directions-panel');
        const shouldAutoCenter = !isNavigating && 
            (!placesPanel || !placesPanel.classList.contains('visible')) &&
            (!directionsPanel || directionsPanel.classList.contains('hidden'));
        
        if (shouldAutoCenter) {
            // Smoothly pan to new location
            map.panTo(location, { animate: true, duration: 0.5 });
        }
    }
    
    // Update the coordinates display if visible
    const coordsDisplay = document.getElementById('current-coords');
    if (coordsDisplay) {
        coordsDisplay.textContent = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
    }
}

function startLocationPolling(intervalMs = 2000) {
    /**
     * Start polling for phone location updates.
     * This enables real-time GPS streaming from iPhone.
     */
    if (locationPollingInterval) {
        clearInterval(locationPollingInterval);
    }
    
    console.log(`Starting location polling every ${intervalMs}ms`);
    
    // Immediate first poll
    pollPhoneLocation();
    
    // Set up interval
    locationPollingInterval = setInterval(pollPhoneLocation, intervalMs);
}

function stopLocationPolling() {
    if (locationPollingInterval) {
        clearInterval(locationPollingInterval);
        locationPollingInterval = null;
        console.log('Location polling stopped');
    }
}

async function pollPhoneLocation() {
    /**
     * Poll the backend for phone GPS location.
     * Falls back to Pi location if phone GPS not available.
     */
    try {
        // Try phone GPS first (iPhone bridge)
        const phoneResponse = await fetch('/api/location/phone');
        const phoneData = await phoneResponse.json();
        
        if (phoneData.ok && phoneData.lat && phoneData.lon) {
            setCurrentLocation(phoneData.lat, phoneData.lon, phoneData.source || 'phone');
            return;
        }
        
        // Fall back to Pi location (less frequent updates are fine here)
        // Only do this if we don't already have a location
        if (!window.currentLocation || window.currentLocation.source === 'default') {
            const piResponse = await fetch('/api/location/pi');
            const piData = await piResponse.json();
            
            if (piData.ok && piData.lat && piData.lon) {
                setCurrentLocation(piData.lat, piData.lon, piData.source || 'pi');
            }
        }
    } catch (error) {
        console.debug('Location poll error:', error);
    }
}

// =============================================================================
// Map Initialization
// =============================================================================

async function initMap() {
    const defaultLocation = [43.6532, -79.3832];
    
    // Initialize map with touch-friendly options for Raspberry Pi
    map = L.map('map', {
        center: defaultLocation,
        zoom: 13,
        zoomControl: true,
        scrollWheelZoom: true,
        touchZoom: true,
        tap: true,
        dragging: true,
        bounceAtZoomLimits: false,
        wheelDebounceTime: 0,
        wheelPxPerZoomLevel: 100,
        // Enable gesture handling if plugin is loaded
        gestureHandling: typeof L.GestureHandling !== 'undefined'
    });
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);
    
    // Setup touch zoom fix for Raspberry Pi
    setupTouchZoomFix();
    
    // Get best available location
    const location = await getBestLocation();
    window.currentLocation = location;
    
    const userLocation = [location.lat, location.lon];
    map.setView(userLocation, 14);
    
    // Set up the current location marker
    setCurrentLocation(location.lat, location.lon, location.source);
    
    // Update UI
    const locationInfo = document.getElementById('location-info');
    if (locationInfo && location.source !== 'default') {
        locationInfo.style.display = 'flex';
    }
    
    // Start polling for real-time location updates (iPhone GPS bridge)
    // Poll every 2 seconds for live GPS from phone
    startLocationPolling(2000);
}

// =============================================================================
// Use My Location
// =============================================================================

async function useMyLocation() {
    const locateBtn = document.getElementById('locate-btn');
    const originInput = document.getElementById('origin-input');
    const coordsDisplay = document.getElementById('current-coords');
    const locationInfo = document.getElementById('location-info');
    
    if (locateBtn) {
        locateBtn.disabled = true;
        locateBtn.innerHTML = 'FINDING...';
    }
    
    try {
        const location = await getBestLocation();
        window.currentLocation = location;
        
        if (originInput) {
            originInput.value = `${location.lat.toFixed(6)}, ${location.lon.toFixed(6)}`;
        }
        
        if (coordsDisplay) {
            coordsDisplay.textContent = `${location.lat.toFixed(6)}, ${location.lon.toFixed(6)}`;
        }
        if (locationInfo) {
            locationInfo.style.display = 'flex';
        }
        
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
            locateBtn.innerHTML = 'USE MY LOCATION';
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

function addPoiMarker(place, index, isClosest = false) {
    const typeLabels = {
        'fuel': 'GAS',
        'gas': 'GAS',
        'restaurant': 'FOOD',
        'food': 'FOOD',
        'parking': 'P',
        'hospital': 'H',
        'pharmacy': 'RX',
        'charging': 'EV',
        'hotel': 'HTL',
        'supermarket': 'MKT'
    };
    
    const label = typeLabels[place.type] || 'POI';
    const bgColor = isClosest ? '#4CAF50' : 'white';
    const textColor = isClosest ? 'white' : '#333';
    
    const icon = L.divIcon({
        className: 'poi-marker',
        html: `<div style="
            background: ${bgColor};
            color: ${textColor};
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            white-space: nowrap;
            border: 2px solid ${isClosest ? '#4CAF50' : '#ddd'};
        ">${label} ${index + 1}</div>`,
        iconSize: null
    });
    
    const marker = L.marker([place.lat, place.lon], { icon })
        .addTo(map)
        .bindPopup(`
            <b>${place.name}</b><br>
            ${place.distance_text}<br>
            ${place.address || ''}
            <br><br>
            <button onclick="navigateToPlace(${place.lat}, ${place.lon}, '${place.name.replace(/'/g, "\\'")}')">
                GO
            </button>
        `);
    
    // Click to select
    marker.on('click', () => {
        selectPlace(place, index);
    });
    
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
// Route Drawing
// =============================================================================

function drawRouteOnMap(route) {
    // Mark as navigating (prevents auto-centering on location updates)
    isNavigating = true;
    
    // Clear previous route
    if (currentRouteLayer) {
        map.removeLayer(currentRouteLayer);
        currentRouteLayer = null;
    }
    
    clearMarkers();
    clearPoiMarkers();
    
    // Get polyline coordinates
    const polyline = route.polyline || route.waypoints || [];
    
    if (polyline.length < 2) {
        console.error('Invalid polyline data');
        showError('Could not display route');
        return;
    }
    
    // Draw the route polyline
    currentRouteLayer = L.polyline(polyline, {
        color: '#1a73e8',
        weight: 6,
        opacity: 0.9,
        lineJoin: 'round'
    }).addTo(map);
    
    // Add start marker
    const startIcon = L.divIcon({
        className: 'route-marker',
        html: `<div style="
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 8px 14px;
            border-radius: 20px;
            font-weight: bold;
            white-space: nowrap;
            box-shadow: 0 3px 10px rgba(17, 153, 142, 0.4);
        ">START</div>`,
        iconSize: null
    });
    
    L.marker(polyline[0], {icon: startIcon}).addTo(map).bindPopup('Starting point');
    
    // Add end marker
    const destName = route.destination_name || 'Destination';
    const truncatedName = destName.length > 18 ? destName.substring(0, 18) + '...' : destName;
    
    const endIcon = L.divIcon({
        className: 'route-marker',
        html: `<div style="
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
            color: white;
            padding: 8px 14px;
            border-radius: 20px;
            font-weight: bold;
            white-space: nowrap;
            box-shadow: 0 3px 10px rgba(235, 51, 73, 0.4);
        ">END: ${truncatedName}</div>`,
        iconSize: null
    });
    
    L.marker(polyline[polyline.length - 1], {icon: endIcon}).addTo(map).bindPopup(destName);
    
    // Fit map to show entire route
    map.fitBounds(currentRouteLayer.getBounds(), { padding: [50, 50] });
    
    // Show turn-by-turn directions
    showTurnByTurn(route);
}

// =============================================================================
// Turn-by-Turn Directions
// =============================================================================

function showTurnByTurn(route) {
    const panel = document.getElementById('directions-panel');
    const summary = document.getElementById('directions-summary');
    const stepsDiv = document.getElementById('directions-steps');
    const banner = document.getElementById('next-turn-banner');
    const turnText = document.getElementById('next-turn-text');
    const turnIcon = document.getElementById('turn-icon');
    const turnDistance = document.getElementById('next-turn-distance');
    
    // Show the panel
    panel.classList.remove('hidden');
    
    // Calculate display values
    const distanceM = route.distance_m || 0;
    const durationS = route.duration_s || 0;
    const distanceMiles = (distanceM / 1609.34).toFixed(1);
    const durationMins = Math.round(durationS / 60);
    const destName = route.destination_name || route.destination_input || 'Destination';
    
    // Build summary
    summary.innerHTML = `
        <div class="summary-row">
            <span class="summary-label">Distance</span>
            <span class="summary-value">${route.distance || distanceMiles + ' mi'}</span>
        </div>
        <div class="summary-row">
            <span class="summary-label">Est. Time</span>
            <span class="summary-value">${route.duration || durationMins + ' min'}</span>
        </div>
        <div class="destination-name">
            TO: ${destName}
        </div>
    `;
    
    // Build steps
    const steps = route.steps || [];
    
    if (steps.length === 0) {
        stepsDiv.innerHTML = `
            <div class="step-item">
                <div class="step-instruction">Head toward your destination</div>
                <div class="step-distance">${route.distance || 'Unknown distance'}</div>
            </div>
        `;
    } else {
        stepsDiv.innerHTML = steps.map((step, index) => {
            const icon = getManeuverIcon(step.type, step.modifier);
            const distanceText = formatStepDistance(step.distance_m);
            
            return `
                <div class="step-item ${index === 0 ? 'active' : ''}" 
                     onclick="focusStep(${step.lat}, ${step.lon})">
                    <div class="step-number">
                        <span class="step-icon">${icon}</span>
                        Step ${index + 1}
                    </div>
                    <div class="step-instruction">${step.instruction}</div>
                    <div class="step-distance">${distanceText}</div>
                </div>
            `;
        }).join('');
    }
    
    // Show next turn banner
    if (steps.length > 0) {
        banner.classList.remove('hidden');
        const firstStep = steps[0];
        const icon = getManeuverIcon(firstStep.type, firstStep.modifier);
        turnIcon.textContent = icon;
        turnText.textContent = firstStep.instruction;
        turnDistance.textContent = formatStepDistance(firstStep.distance_m);
    } else {
        banner.classList.add('hidden');
    }
}

function getManeuverIcon(type, modifier) {
    // Map maneuver types to text icons (Pi-compatible)
    const icons = {
        'depart': '[GO]',
        'arrive': '[END]',
        'turn': modifier === 'left' ? '[L]' : modifier === 'right' ? '[R]' : '[^]',
        'new name': '[^]',
        'merge': '[M]',
        'on ramp': '[ON]',
        'off ramp': '[OFF]',
        'fork': modifier === 'left' ? '[FL]' : '[FR]',
        'end of road': modifier === 'left' ? '[L]' : '[R]',
        'continue': '[^]',
        'roundabout': '[O]',
        'rotary': '[O]',
        'roundabout turn': '[O]',
        'exit roundabout': '[EX]',
        'exit rotary': '[EX]'
    };
    
    // Check modifier for turn direction
    if (type === 'turn' || type === 'end of road' || type === 'fork') {
        if (modifier === 'left' || modifier === 'sharp left' || modifier === 'slight left') {
            return '[L]';
        } else if (modifier === 'right' || modifier === 'sharp right' || modifier === 'slight right') {
            return '[R]';
        } else if (modifier === 'uturn') {
            return '[U]';
        }
    }
    
    return icons[type] || '[^]';
}

function formatStepDistance(meters) {
    if (!meters || meters < 0) return '';
    
    if (meters < 100) {
        return `${Math.round(meters)} m`;
    } else if (meters < 1000) {
        return `${Math.round(meters / 10) * 10} m`;
    } else {
        const miles = meters / 1609.34;
        return `${miles.toFixed(1)} mi`;
    }
}

function focusStep(lat, lon) {
    if (lat && lon) {
        map.setView([lat, lon], 17);
    }
}

function closeDirectionsPanel() {
    const panel = document.getElementById('directions-panel');
    const banner = document.getElementById('next-turn-banner');
    
    panel.classList.add('hidden');
    banner.classList.add('hidden');
    
    // No longer navigating
    isNavigating = false;
    
    // Clear route
    if (currentRouteLayer) {
        map.removeLayer(currentRouteLayer);
        currentRouteLayer = null;
    }
    
    clearMarkers();
    
    // Reset the current location marker (will be recreated by next poll)
    currentLocationMarker = null;
    
    // Recenter on user location
    if (window.currentLocation) {
        map.setView([window.currentLocation.lat, window.currentLocation.lon], 14);
        // Marker will be recreated by the next location poll
        setCurrentLocation(window.currentLocation.lat, window.currentLocation.lon, window.currentLocation.source);
    }
}

// Make closeDirectionsPanel globally available
window.closeDirectionsPanel = closeDirectionsPanel;
window.focusStep = focusStep;

// =============================================================================
// Places Search with Panel
// =============================================================================

async function searchNearbyPlaces(placeType) {
    if (!window.currentLocation) {
        showError('Getting your location first...');
        await useMyLocation();
        if (!window.currentLocation) {
            showError('Could not get location');
            return;
        }
    }
    
    // Close directions panel if open
    closeDirectionsPanel();
    
    // Update button state
    const btn = document.getElementById(`btn-${placeType}`);
    document.querySelectorAll('.quick-btn').forEach(b => b.classList.remove('active'));
    if (btn) {
        btn.classList.add('active');
        btn.disabled = true;
        btn.innerHTML = `<span class="loading-spinner"></span>`;
    }
    
    // Show panel with loading state
    showPlacesPanel('Searching...', []);
    
    try {
        const url = `/api/places/nearby?lat=${window.currentLocation.lat}&lon=${window.currentLocation.lon}&type=${placeType}&radius=8000`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.ok && data.results && data.results.length > 0) {
            // Clear old markers
            clearPoiMarkers();
            
            // Add markers for each place
            data.results.forEach((place, index) => {
                if (place.lat && place.lon) {
                    addPoiMarker(place, index, index === 0);
                }
            });
            
            // Show panel with results
            showPlacesPanel(data.type_name || placeType, data.results);
            
            // Fit map to show all markers
            if (poiMarkers.length > 0) {
                const group = new L.featureGroup(poiMarkers);
                map.fitBounds(group.getBounds().pad(0.1));
            }
            
        } else {
            showPlacesPanel(data.type_name || placeType, [], 'No places found nearby');
        }
    } catch (error) {
        console.error('Places search error:', error);
        showPlacesPanel(placeType, [], 'Search failed. Try again.');
    } finally {
        // Reset button
        if (btn) {
            btn.disabled = false;
            const names = { fuel: 'GAS', restaurant: 'FOOD', parking: 'PARK', hospital: 'HOSP' };
            btn.innerHTML = names[placeType] || placeType.toUpperCase();
        }
    }
}

function showPlacesPanel(title, places, errorMsg = null) {
    const panel = document.getElementById('places-panel');
    const panelTitle = document.getElementById('places-panel-title');
    const placesCount = document.getElementById('places-count');
    const placesList = document.getElementById('places-list');
    
    panel.classList.add('visible');
    panelTitle.textContent = title;
    
    if (errorMsg) {
        placesCount.textContent = '';
        placesList.innerHTML = `
            <div class="no-results">
                <div class="no-results-icon">😕</div>
                <div>${errorMsg}</div>
            </div>
        `;
        return;
    }
    
    if (places.length === 0) {
        placesCount.textContent = 'Searching...';
        placesList.innerHTML = `
            <div class="no-results">
                <div class="loading-spinner" style="border-top-color: #667eea;"></div>
            </div>
        `;
        return;
    }
    
    placesCount.textContent = `Found ${places.length} nearby`;
    
    placesList.innerHTML = places.map((place, index) => `
        <div class="place-card ${index === 0 ? 'closest' : ''}" 
             data-index="${index}"
             onclick="selectPlace(window._places[${index}], ${index})">
            <div class="place-card-name">
                ${index + 1}. ${place.name}
                ${index === 0 ? '<span class="closest-badge">CLOSEST</span>' : ''}
            </div>
            <div class="place-card-distance">${place.distance_text}</div>
            ${place.address ? `<div class="place-card-address">${place.address}</div>` : ''}
            <button class="place-card-btn" onclick="event.stopPropagation(); navigateToPlace(${place.lat}, ${place.lon}, '${place.name.replace(/'/g, "\\'")}')">
                GO HERE
            </button>
        </div>
    `).join('');
    
    // Store places for click handlers
    window._places = places;
}

function closePlacesPanel() {
    const panel = document.getElementById('places-panel');
    panel.classList.remove('visible');
    clearPoiMarkers();
    document.querySelectorAll('.quick-btn').forEach(b => b.classList.remove('active'));
    
    // Recenter on user location
    if (window.currentLocation) {
        map.setView([window.currentLocation.lat, window.currentLocation.lon], 14);
    }
}

function selectPlace(place, index) {
    selectedPlace = place;
    
    // Update card highlighting
    document.querySelectorAll('.place-card').forEach((card, i) => {
        card.classList.remove('selected');
        if (i === index) {
            card.classList.add('selected');
        }
    });
    
    // Center map on place
    map.setView([place.lat, place.lon], 16);
    
    // Open popup
    if (poiMarkers[index]) {
        poiMarkers[index].openPopup();
    }
}

// =============================================================================
// Navigation to Place
// =============================================================================

async function navigateToPlace(lat, lon, name) {
    if (!window.currentLocation) {
        showError('Please get your location first');
        return;
    }
    
    showSuccess(`Getting route to ${name}...`);
    
    // Close places panel
    closePlacesPanel();
    
    // Update destination input
    const destInput = document.getElementById('dest-input');
    if (destInput) {
        destInput.value = name;
    }
    
    // Use Google Directions for turn-by-turn navigation
    const origin = { lat: window.currentLocation.lat, lon: window.currentLocation.lon };
    const dest = { lat: lat, lon: lon };
    
    try {
        // Try Google route first (has better turn-by-turn)
        await showGoogleRouteOnMap(origin, dest);
    } catch (error) {
        console.error('Google route error, trying fallback:', error);
        
        // Fallback to OSRM-based route
        try {
            const url = `/api/route/to_place?start_lat=${window.currentLocation.lat}&start_lon=${window.currentLocation.lon}&lat=${lat}&lon=${lon}&name=${encodeURIComponent(name)}`;
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.ok || data.success) {
                drawRouteOnMap(data);
            } else {
                showError(data.error || data.message || 'Could not calculate route');
            }
        } catch (fallbackError) {
            console.error('Fallback navigation error:', fallbackError);
            showError('Failed to get directions');
        }
    }
}

// Make navigateToPlace available globally
window.navigateToPlace = navigateToPlace;

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
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            box-shadow: 0 4px 15px rgba(17, 153, 142, 0.4);
            z-index: 2000;
            font-weight: 600;
        `;
        document.body.appendChild(panel);
    }
    
    panel.innerHTML = `OK: ${message}`;
    panel.style.display = 'block';
    
    setTimeout(() => { panel.style.display = 'none'; }, 3000);
}

function showError(message) {
    let errorPanel = document.getElementById('error-panel');
    if (!errorPanel) {
        errorPanel = document.createElement('div');
        errorPanel.id = 'error-panel';
        errorPanel.style.cssText = `
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            box-shadow: 0 4px 15px rgba(235, 51, 73, 0.4);
            z-index: 2000;
            font-weight: 600;
        `;
        document.body.appendChild(errorPanel);
    }
    
    errorPanel.innerHTML = `ERROR: ${message}`;
    errorPanel.style.display = 'block';
    
    setTimeout(() => { errorPanel.style.display = 'none'; }, 4000);
}

// =============================================================================
// Routing (Manual entry)
// =============================================================================

async function calculateRoute(origin, destination) {
    setLoading(true);
    closeDirectionsPanel();
    
    try {
        const response = await fetch('/api/map/route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origin, destination })
        });
        const data = await response.json();
        
        if (data.success) {
            drawRouteOnMap(data);
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
    
    // Map click for destination selection (long press or double tap)
    // We use a delayed click to avoid interfering with normal panning
    let clickTimeout = null;
    let lastClickTime = 0;
    
    // Wait for map to be initialized
    setTimeout(() => {
        if (map) {
            // Double-click to set destination and get route
            map.on('dblclick', async (e) => {
                e.originalEvent.preventDefault();
                
                const dest = { lat: e.latlng.lat, lon: e.latlng.lng };
                
                // Get current location as origin
                let origin = window.currentLocation;
                
                if (!origin) {
                    // Try to get location first
                    showSuccess('Getting your location...');
                    origin = await getBestLocation();
                    window.currentLocation = origin;
                }
                
                if (origin && origin.lat && origin.lon) {
                    // Show destination marker temporarily
                    const tempMarker = L.marker([dest.lat, dest.lon]).addTo(map);
                    tempMarker.bindPopup('Getting route...').openPopup();
                    
                    // Get and show route
                    await showGoogleRouteOnMap(origin, dest);
                    
                    // Remove temp marker (route will show its own)
                    map.removeLayer(tempMarker);
                } else {
                    showError('Could not get your location');
                }
            });
            
            console.log('Map click handler enabled - double-click to navigate');
        }
    }, 1000);
});

// Make functions available globally
window.searchNearbyPlaces = searchNearbyPlaces;
window.closePlacesPanel = closePlacesPanel;
window.selectPlace = selectPlace;
