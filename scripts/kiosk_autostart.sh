#!/bin/bash
#
# Kiosk Mode Autostart Script for Raspberry Pi
# Add to /etc/xdg/lxsession/LXDE-pi/autostart or ~/.config/lxsession/LXDE-pi/autostart
#
# Installation:
#   1. Copy this script: sudo cp kiosk_autostart.sh /usr/local/bin/
#   2. Make executable: sudo chmod +x /usr/local/bin/kiosk_autostart.sh
#   3. Add to autostart: echo "@/usr/local/bin/kiosk_autostart.sh" >> ~/.config/lxsession/LXDE-pi/autostart
#

SCRIPT_DIR="/home/pi/car_stereo_system"
LOG_FILE="/tmp/car-stereo-kiosk.log"

# Redirect output to log
exec > "$LOG_FILE" 2>&1

echo "$(date): Starting Car Stereo System in Kiosk Mode"

# Wait for desktop to be ready
sleep 10

# Disable screen blanking and power management
xset s off
xset -dpms
xset s noblank

# Hide mouse cursor after 3 seconds of inactivity
if command -v unclutter &> /dev/null; then
    unclutter -idle 3 &
fi

# Kill any existing instances
pkill -f "chromium-browser.*localhost:5000" || true
pkill -f "app.py" || true
pkill -f "carplay_engine/out/app" || true

# Start the car stereo system in full mode
cd "$SCRIPT_DIR"
./start.sh --full &

echo "$(date): Car Stereo System started"

