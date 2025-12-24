/**
 * Phone Screen - Pure BlueZ HFP Integration
 * Real-time call state via Server-Sent Events
 */

// State
let isConnected = false;
let callActive = false;
let callStartTime = null;
let durationInterval = null;

// DOM elements
const statusDot = document.getElementById('status-dot');
const statusEl = document.getElementById('status');
const deviceNameEl = document.getElementById('device-name');
const incomingEl = document.getElementById('incoming');
const callerEl = document.getElementById('caller');
const stateEl = document.getElementById('state');
const callIcon = document.getElementById('call-icon');
const answerBtn = document.getElementById('answer-btn');
const durationEl = document.getElementById('duration');
const callList = document.getElementById('call-list');

// Initialize SSE connection
let eventSource = null;

document.addEventListener('DOMContentLoaded', () => {
    connectEventSource();
    fetchInitialStatus();
});

/**
 * Connect to Server-Sent Events for real-time updates
 */
function connectEventSource() {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource('/api/phone/events');
    
    eventSource.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            
            // Skip heartbeat messages
            if (data.heartbeat) return;
            
            handleUpdate(data);
        } catch (err) {
            console.error('Error parsing event:', err);
        }
    };
    
    eventSource.onerror = (e) => {
        console.log('SSE connection error, reconnecting in 3s...');
        setTimeout(connectEventSource, 3000);
    };
    
    eventSource.onopen = () => {
        console.log('SSE connected');
    };
}

/**
 * Fetch initial status via REST API
 */
async function fetchInitialStatus() {
    try {
        const response = await fetch('/api/phone/status');
        const data = await response.json();
        handleUpdate(data);
    } catch (err) {
        console.error('Error fetching status:', err);
    }
}

/**
 * Handle phone status update
 */
function handleUpdate(data) {
    // Update connection status
    isConnected = data.connected || false;
    
    if (isConnected) {
        statusDot.classList.add('connected');
        statusEl.textContent = 'Connected';
        deviceNameEl.textContent = data.device_name || data.device || '';
    } else {
        statusDot.classList.remove('connected');
        statusEl.textContent = 'Waiting for phone…';
        deviceNameEl.textContent = '';
    }
    
    // Handle call state
    const callState = data.call_state || data.state || 'idle';
    
    if (callState === 'idle') {
        hideCall();
    } else {
        showCall(callState, data.caller_id || data.caller, data.caller_name);
    }
    
    // Update recent calls
    if (data.recent_calls && data.recent_calls.length > 0) {
        updateRecentCalls(data.recent_calls);
    }
}

/**
 * Show incoming/active call UI
 */
function showCall(state, callerId, callerName) {
    incomingEl.classList.remove('hidden', 'ringing', 'active');
    
    // Set caller info
    callerEl.textContent = callerName || callerId || 'Unknown Caller';
    
    switch (state) {
        case 'incoming':
            incomingEl.classList.add('ringing');
            stateEl.textContent = 'Incoming Call';
            callIcon.textContent = 'RING';
            answerBtn.classList.remove('hidden');
            durationEl.classList.add('hidden');
            stopDurationTimer();
            break;
            
        case 'active':
            incomingEl.classList.add('active');
            stateEl.textContent = 'On Call';
            callIcon.textContent = 'CALL';
            answerBtn.classList.add('hidden');
            durationEl.classList.remove('hidden');
            startDurationTimer();
            break;
            
        case 'outgoing':
        case 'alerting':
            incomingEl.classList.add('active');
            stateEl.textContent = 'Calling...';
            callIcon.textContent = 'DIAL';
            answerBtn.classList.add('hidden');
            durationEl.classList.add('hidden');
            break;
            
        case 'held':
            stateEl.textContent = 'On Hold';
            callIcon.textContent = 'HOLD';
            break;
            
        default:
            stateEl.textContent = state;
    }
    
    callActive = true;
}

/**
 * Hide call UI
 */
function hideCall() {
    incomingEl.classList.add('hidden');
    incomingEl.classList.remove('ringing', 'active');
    stopDurationTimer();
    callActive = false;
}

/**
 * Start call duration timer
 */
function startDurationTimer() {
    if (durationInterval) return;
    
    callStartTime = callStartTime || Date.now();
    
    durationInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
        const mins = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const secs = (elapsed % 60).toString().padStart(2, '0');
        durationEl.textContent = `${mins}:${secs}`;
    }, 1000);
}

/**
 * Stop call duration timer
 */
function stopDurationTimer() {
    if (durationInterval) {
        clearInterval(durationInterval);
        durationInterval = null;
    }
    callStartTime = null;
    durationEl.textContent = '00:00';
}

/**
 * Answer incoming call
 */
async function answer() {
    try {
        const response = await fetch('/api/phone/answer', { method: 'POST' });
        const data = await response.json();
        
        if (!data.success && data.message) {
            console.error('Answer failed:', data.message);
        }
    } catch (err) {
        console.error('Error answering call:', err);
    }
}

/**
 * Reject/hang up call
 */
async function reject() {
    try {
        const response = await fetch('/api/phone/hangup', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            hideCall();
        }
    } catch (err) {
        console.error('Error rejecting call:', err);
    }
}

/**
 * Update recent calls list
 */
function updateRecentCalls(calls) {
    if (!calls || calls.length === 0) {
        callList.innerHTML = `
            <li class="empty-state">
                    <div class="icon">PHONE</div>
                <p>No recent calls</p>
                <p><small>Your call history will appear here</small></p>
            </li>
        `;
        return;
    }
    
    callList.innerHTML = calls.map(call => {
        const icon = call.type === 'missed' ? 'X' :
                     call.type === 'outgoing' ? 'OUT' : 'IN';
        const typeLabel = call.type === 'missed' ? 'Missed' :
                         call.type === 'outgoing' ? 'Outgoing' : 'Incoming';
        
        return `
            <li class="call-item">
                <span class="call-item-icon">${icon}</span>
                <div class="call-item-info">
                    <div class="call-item-name">${call.name || call.number || 'Unknown'}</div>
                    <div class="call-item-time">${call.time || ''}</div>
                </div>
                <span class="call-item-type ${call.type || 'incoming'}">${typeLabel}</span>
            </li>
        `;
    }).join('');
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (eventSource) {
        eventSource.close();
    }
});
