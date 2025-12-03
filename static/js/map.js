// Map navigation JavaScript
// Supports both coordinates and street address input

let map;
let routeLayer;
let markers = [];

// Initialize map
function initMap() {
    // Default location (Toronto - adjust as needed)
    const defaultLocation = [43.6532, -79.3832];
    
    map = L.map('map').setView(defaultLocation, 13);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);
    
    // Try to get user's location
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const userLocation = [position.coords.latitude, position.coords.longitude];
                map.setView(userLocation, 15);
                addMarker(userLocation, 'Your Location', 'blue');
            },
            (error) => {
                console.log('Geolocation error:', error);
                // Use default location
                addMarker(defaultLocation, 'Default Location', 'gray');
            }
        );
    } else {
        // Use default location
        addMarker(defaultLocation, 'Default Location', 'gray');
    }
}

// Add a marker to the map
function addMarker(location, popupText, color = 'blue') {
    const marker = L.marker(location).addTo(map).bindPopup(popupText);
    markers.push(marker);
    return marker;
}

// Clear all markers except user location
function clearMarkers() {
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
}

// Show loading state
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

// Show route info panel
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

// Hide route info panel
function hideRouteInfo() {
    const infoPanel = document.getElementById('route-info-panel');
    if (infoPanel) {
        infoPanel.style.display = 'none';
    }
}

// Show error message
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
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorPanel.style.display = 'none';
    }, 5000);
}

// Get route - main function
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
    // Clear existing markers and route
    clearMarkers();
    if (routeLayer) {
        map.removeLayer(routeLayer);
    }
    
    const waypoints = data.waypoints;
    
    if (waypoints && waypoints.length >= 2) {
        const origin = waypoints[0];
        const destination = waypoints[waypoints.length - 1];
        
        // Add markers for origin and destination
        const originLabel = data.origin_input || `${origin[0].toFixed(4)}, ${origin[1].toFixed(4)}`;
        const destLabel = data.destination_input || `${destination[0].toFixed(4)}, ${destination[1].toFixed(4)}`;
        
        // Custom icons
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
        
        // Draw route line
        routeLayer = L.polyline(waypoints, {
            color: '#667eea',
            weight: 6,
            opacity: 0.8,
            dashArray: '10, 10'
        }).addTo(map);
        
        // Fit map to show entire route with padding
        map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });
    }
}

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', () => {
    initMap();
});