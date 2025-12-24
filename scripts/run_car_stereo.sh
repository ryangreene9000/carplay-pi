#!/bin/bash
#
# Car Stereo System — Full Launcher
# Starts the entire system with one command
# Designed for Raspberry Pi 5 with 7" touchscreen
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}     🚗  Car Stereo System — Full Launcher                   ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# =============================================================================
# Detect LAN IP Address
# =============================================================================

detect_ip() {
    # Try hostname -I first
    LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    
    # Fallback to ip route
    if [[ -z "$LAN_IP" ]]; then
        LAN_IP=$(ip route get 8.8.8.8 2>/dev/null | awk '/src/ {print $7}')
    fi
    
    # Fallback to ifconfig
    if [[ -z "$LAN_IP" ]]; then
        LAN_IP=$(ifconfig 2>/dev/null | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -n1)
    fi
    
    # Final fallback
    if [[ -z "$LAN_IP" ]]; then
        LAN_IP="localhost"
        echo -e "${YELLOW}⚠️  Could not detect LAN IP, using localhost${NC}"
    fi
}

detect_ip
echo -e "${GREEN}📡 Detected IP:${NC} $LAN_IP"

# Export for Flask templates
export CAR_STEREO_LAN_IP="$LAN_IP"
export CAR_STEREO_PORT="5000"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  📱 Access URLs:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}Main Interface:${NC}      http://$LAN_IP:5000"
echo -e "  ${GREEN}iPhone GPS Bridge:${NC}   http://$LAN_IP:5000/ios_bridge"
echo -e "  ${GREEN}Map Navigation:${NC}      http://$LAN_IP:5000/map"
echo -e "  ${GREEN}Music Player:${NC}        http://$LAN_IP:5000/music"
echo ""

# =============================================================================
# Check and activate virtual environment
# =============================================================================

echo -e "${YELLOW}🔧 Setting up environment...${NC}"

if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo "   Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Quick dependency check
python3 -c "import flask" 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Installing missing dependencies...${NC}"
    pip install -r requirements.txt --quiet
}

# =============================================================================
# WiFi Scan Permission (for Google Geolocation)
# =============================================================================

setup_wifi_permission() {
    # Check if iw can scan without sudo
    if iw dev wlan0 scan 2>/dev/null | head -1 | grep -q "BSS"; then
        echo -e "${GREEN}✓ WiFi scanning already enabled${NC}"
        return 0
    fi
    
    # Try to grant capability to iw
    IW_PATH=$(which iw 2>/dev/null)
    if [[ -n "$IW_PATH" ]]; then
        echo -e "${YELLOW}🔐 Granting WiFi scan permission (requires sudo once)...${NC}"
        if sudo setcap cap_net_admin+ep "$IW_PATH" 2>/dev/null; then
            echo -e "${GREEN}✓ WiFi scan permission granted${NC}"
            return 0
        fi
    fi
    
    # If that failed, we'll need to run the scan commands with sudo
    # Check if user can sudo without password for iw
    if sudo -n iw dev wlan0 scan 2>/dev/null | head -1 | grep -q "BSS"; then
        echo -e "${GREEN}✓ WiFi scanning via sudo${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  WiFi scanning may require manual setup${NC}"
    echo -e "   Run: ${CYAN}sudo setcap cap_net_admin+ep \$(which iw)${NC}"
    echo -e "   Or add to sudoers: ${CYAN}$USER ALL=(ALL) NOPASSWD: /usr/sbin/iw${NC}"
    return 1
}

echo ""
echo -e "${YELLOW}🛜 Setting up WiFi geolocation...${NC}"
setup_wifi_permission

# =============================================================================
# Parse command line arguments
# =============================================================================

KIOSK_MODE=false
NO_BROWSER=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --kiosk)
            KIOSK_MODE=true
            shift
            ;;
        --no-browser)
            NO_BROWSER=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./run_car_stereo.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --kiosk       Launch in fullscreen kiosk mode (Pi touchscreen)"
            echo "  --no-browser  Don't auto-open browser"
            echo "  --help        Show this help"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# =============================================================================
# Launch Chromium in kiosk mode (for Pi touchscreen)
# =============================================================================

launch_browser() {
    if [[ "$NO_BROWSER" == "true" ]]; then
        return
    fi
    
    # Wait for Flask to start
    sleep 3
    
    if [[ "$KIOSK_MODE" == "true" ]]; then
        echo -e "${CYAN}🖥️  Launching fullscreen kiosk mode...${NC}"
        
        # Disable screen blanking
        xset -dpms 2>/dev/null || true
        xset s off 2>/dev/null || true
        
        # Hide cursor after 0.5 seconds of inactivity
        unclutter -idle 0.5 2>/dev/null &
        
        # Kill any existing Chromium
        pkill -f chromium 2>/dev/null || true
        sleep 1
        
        # Launch Chromium in kiosk mode
        DISPLAY=:0 chromium-browser \
            --kiosk \
            --incognito \
            --disable-infobars \
            --disable-session-crashed-bubble \
            --disable-restore-session-state \
            --noerrdialogs \
            --disable-translate \
            --no-first-run \
            --fast \
            --fast-start \
            --disable-features=TranslateUI \
            --disk-cache-dir=/dev/null \
            --overscroll-history-navigation=0 \
            "http://$LAN_IP:5000" &
    else
        echo -e "${CYAN}🌐 Opening browser...${NC}"
        
        # Try to open default browser
        if command -v xdg-open &> /dev/null; then
            xdg-open "http://$LAN_IP:5000" 2>/dev/null &
        elif command -v chromium-browser &> /dev/null; then
            chromium-browser "http://$LAN_IP:5000" 2>/dev/null &
        elif command -v firefox &> /dev/null; then
            firefox "http://$LAN_IP:5000" 2>/dev/null &
        fi
    fi
}

# =============================================================================
# Cleanup on exit
# =============================================================================

cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down Car Stereo System...${NC}"
    
    # Kill browser if in kiosk mode
    if [[ "$KIOSK_MODE" == "true" ]]; then
        pkill -f chromium 2>/dev/null || true
    fi
    
    # Kill any background jobs
    jobs -p | xargs -r kill 2>/dev/null || true
    
    echo -e "${GREEN}✓ Shutdown complete${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# =============================================================================
# Start the Flask backend with auto-restart
# =============================================================================

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 Starting Car Stereo System...${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Press CTRL+C to stop${NC}"
echo ""

# Launch browser in background
launch_browser &

# Main loop - restart Flask if it crashes
RESTART_COUNT=0
MAX_RESTARTS=10

while true; do
    echo -e "${GREEN}▶ Starting Flask backend...${NC}"
    
    # Run Flask
    python3 app.py
    EXIT_CODE=$?
    
    # Check if we should restart
    if [[ $EXIT_CODE -eq 0 ]]; then
        # Clean exit
        break
    fi
    
    RESTART_COUNT=$((RESTART_COUNT + 1))
    
    if [[ $RESTART_COUNT -ge $MAX_RESTARTS ]]; then
        echo -e "${RED}❌ Flask crashed $MAX_RESTARTS times. Stopping.${NC}"
        break
    fi
    
    echo ""
    echo -e "${YELLOW}⚠️  Flask crashed (exit code: $EXIT_CODE)${NC}"
    echo -e "${YELLOW}   Restarting in 3 seconds... (attempt $RESTART_COUNT/$MAX_RESTARTS)${NC}"
    sleep 3
done

cleanup

