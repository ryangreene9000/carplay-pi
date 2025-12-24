#!/bin/bash
#
# Car Stereo System - Unified Startup Script
# Raspberry Pi 5 with 7" Touchscreen
#
# This script starts both the Flask backend and optionally CarPlay
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║              🚗 Car Stereo System v1.0                       ║"
    echo "║         Raspberry Pi 5 • 7\" Touchscreen • CarPlay            ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if virtual environment exists, create if not
setup_venv() {
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
        source venv/bin/activate
        echo -e "${YELLOW}Installing dependencies...${NC}"
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
}

# Check if CarPlay is built
check_carplay() {
    if [ -f "$SCRIPT_DIR/carplay_engine/out/app" ]; then
        echo -e "${GREEN}✓ CarPlay engine: Built${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ CarPlay engine: Not built${NC}"
        echo -e "  Run ${BLUE}./build_carplay.sh${NC} to build"
        return 1
    fi
}

# Create named pipe for CarPlay commands
setup_carplay_pipe() {
    PIPE_PATH="/tmp/fastcarplay_pipe"
    if [ ! -p "$PIPE_PATH" ]; then
        mkfifo "$PIPE_PATH" 2>/dev/null || true
        chmod 666 "$PIPE_PATH" 2>/dev/null || true
    fi
}

# Start Flask backend
start_flask() {
    echo -e "${GREEN}Starting Flask backend on port 5000...${NC}"
    # Note: ALSA warnings may appear but are harmless - they occur when
    # enumerating audio devices and some devices don't exist
    python3 app.py &
    FLASK_PID=$!
    echo "Flask PID: $FLASK_PID"
    sleep 2
    
    if kill -0 $FLASK_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Flask backend started${NC}"
    else
        echo -e "${RED}✗ Flask backend failed to start${NC}"
        exit 1
    fi
}

# Start CarPlay engine (optional)
start_carplay() {
    if [ -f "$SCRIPT_DIR/carplay_engine/out/app" ]; then
        echo -e "${GREEN}Starting CarPlay engine...${NC}"
        
        CARPLAY_SETTINGS="$SCRIPT_DIR/carplay_engine/conf/settings.txt"
        if [ ! -f "$CARPLAY_SETTINGS" ]; then
            mkdir -p "$SCRIPT_DIR/carplay_engine/conf"
            cp "$SCRIPT_DIR/carplay_engine/settings.txt" "$CARPLAY_SETTINGS" 2>/dev/null || true
        fi
        
        cd "$SCRIPT_DIR/carplay_engine"
        DISPLAY=:0 ./out/app ./conf/settings.txt &
        CARPLAY_PID=$!
        cd "$SCRIPT_DIR"
        
        echo "CarPlay PID: $CARPLAY_PID"
        sleep 2
        
        if kill -0 $CARPLAY_PID 2>/dev/null; then
            echo -e "${GREEN}✓ CarPlay engine started${NC}"
        else
            echo -e "${YELLOW}⚠ CarPlay engine may have failed (check dongle connection)${NC}"
        fi
    fi
}

# Open browser in kiosk mode
start_kiosk() {
    echo -e "${GREEN}Opening browser in kiosk mode...${NC}"
    
    # Wait for Flask to be ready
    sleep 3
    
    # Disable screen blanking
    if command -v xset &> /dev/null; then
        DISPLAY=:0 xset s off
        DISPLAY=:0 xset -dpms
        DISPLAY=:0 xset s noblank
    fi
    
    # Start Chromium in kiosk mode
    if command -v chromium-browser &> /dev/null; then
        DISPLAY=:0 chromium-browser \
            --kiosk \
            --noerrdialogs \
            --disable-infobars \
            --disable-session-crashed-bubble \
            --disable-restore-session-state \
            --no-first-run \
            --start-fullscreen \
            --autoplay-policy=no-user-gesture-required \
            "http://localhost:5000" &
        BROWSER_PID=$!
        echo "Browser PID: $BROWSER_PID"
    elif command -v firefox &> /dev/null; then
        DISPLAY=:0 firefox --kiosk "http://localhost:5000" &
        BROWSER_PID=$!
        echo "Browser PID: $BROWSER_PID"
    else
        echo -e "${YELLOW}⚠ No browser found for kiosk mode${NC}"
        echo -e "  Open http://localhost:5000 manually"
    fi
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    
    # Kill Flask
    if [ ! -z "$FLASK_PID" ]; then
        kill $FLASK_PID 2>/dev/null
    fi
    
    # Kill CarPlay
    if [ ! -z "$CARPLAY_PID" ]; then
        kill $CARPLAY_PID 2>/dev/null
    fi
    
    # Kill browser
    if [ ! -z "$BROWSER_PID" ]; then
        kill $BROWSER_PID 2>/dev/null
    fi
    
    echo -e "${GREEN}Goodbye!${NC}"
    exit 0
}

# Trap signals for cleanup
trap cleanup SIGINT SIGTERM

# Main execution
main() {
    print_banner
    
    # Parse arguments
    KIOSK_MODE=false
    WITH_CARPLAY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --kiosk|-k)
                KIOSK_MODE=true
                shift
                ;;
            --carplay|-c)
                WITH_CARPLAY=true
                shift
                ;;
            --full|-f)
                KIOSK_MODE=true
                WITH_CARPLAY=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --kiosk, -k     Start in kiosk mode (fullscreen browser)"
                echo "  --carplay, -c   Auto-start CarPlay engine"
                echo "  --full, -f      Full mode (kiosk + carplay)"
                echo "  --help, -h      Show this help"
                echo ""
                echo "Examples:"
                echo "  $0              Start Flask backend only"
                echo "  $0 --kiosk      Start with fullscreen browser"
                echo "  $0 --full       Start everything (production mode)"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Setup environment
    setup_venv
    setup_carplay_pipe
    check_carplay
    
    echo ""
    
    # Start services
    start_flask
    
    if [ "$WITH_CARPLAY" = true ]; then
        start_carplay
    fi
    
    if [ "$KIOSK_MODE" = true ]; then
        start_kiosk
    fi
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Car Stereo System is running!${NC}"
    echo -e "${GREEN}  Open: ${BLUE}http://localhost:5000${NC}"
    echo -e "${GREEN}  Press Ctrl+C to stop${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Wait for Flask process
    wait $FLASK_PID
}

main "$@"
