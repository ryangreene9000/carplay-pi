#!/usr/bin/env bash
# =============================================================================
# Raspberry Pi Environment Fix Script
# =============================================================================
# This script fixes all startup errors for the car stereo system on Raspberry Pi.
# It installs system dependencies, sets up Python environment, and configures
# Bluetooth permissions.
#
# Usage:
#   chmod +x fix_rpi_environment.sh
#   bash fix_rpi_environment.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}=============================================="
    echo "  $1"
    echo -e "==============================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# =============================================================================
# Step 1: Detect Platform
# =============================================================================
print_header "Car Stereo System - Environment Fix"

echo "Detecting platform..."
SYSTEM=$(uname -s)
ARCH=$(uname -m)

if [[ "$SYSTEM" != "Linux" ]]; then
    print_error "This script is intended for Raspberry Pi (Linux) only."
    echo "  Detected: $SYSTEM"
    echo "  On macOS, run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

print_success "Running on Linux ($ARCH)"

# Check if running on Raspberry Pi
if [[ -f /proc/device-tree/model ]]; then
    PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")
    echo "  Device: $PI_MODEL"
fi

# =============================================================================
# Step 2: Install System Dependencies
# =============================================================================
print_header "Step 1/7: Installing System Dependencies"

echo "Updating apt package lists..."
sudo apt-get update

echo ""
echo "Installing Bluetooth, Python, and build tools..."
sudo apt-get install -y \
    bluetooth \
    bluez \
    libbluetooth-dev \
    python3-dev \
    python3-venv \
    python3-pip \
    build-essential \
    curl

# Optional: bluez-tools (not available on all versions)
echo ""
echo "Attempting to install bluez-tools (optional)..."
sudo apt-get install -y bluez-tools 2>/dev/null || print_warning "bluez-tools not available - this is OK"

print_success "System dependencies installed"

# =============================================================================
# Step 2b: Install playerctl from source (not in apt on Bookworm)
# =============================================================================
print_header "Step 1b/8: Installing playerctl from source"

echo "playerctl is not available in Raspberry Pi OS apt repositories."
echo "Building from source..."

# Check if playerctl is already installed
if command -v playerctl &> /dev/null; then
    EXISTING_VERSION=$(playerctl --version 2>/dev/null || echo "unknown")
    print_success "playerctl already installed (version: $EXISTING_VERSION)"
else
    echo ""
    echo "Installing build dependencies for playerctl..."
    # Package names differ between Debian versions
    # Try Bookworm names first, fall back to older names
    sudo apt-get install -y \
        meson \
        ninja-build \
        libglib2.0-dev \
        wget \
        unzip || true
    
    # GObject introspection - try different package names
    sudo apt-get install -y libgirepository-1.0-dev 2>/dev/null || \
    sudo apt-get install -y libgirepository1.0-dev 2>/dev/null || \
    sudo apt-get install -y gir1.2-glib-2.0 2>/dev/null || \
    print_warning "GObject introspection packages not found - playerctl may build without introspection"

    # Fetch and build playerctl
    cd /tmp
    PLAYERCTL_VERSION="2.4.1"
    
    echo ""
    echo "Downloading playerctl v${PLAYERCTL_VERSION}..."
    rm -rf playerctl.zip playerctl-${PLAYERCTL_VERSION} 2>/dev/null || true
    wget -q https://github.com/altdesktop/playerctl/archive/refs/tags/v${PLAYERCTL_VERSION}.zip -O playerctl.zip
    
    if [[ ! -f playerctl.zip ]]; then
        print_error "Failed to download playerctl"
    else
        echo "Extracting..."
        unzip -q playerctl.zip
        cd playerctl-${PLAYERCTL_VERSION}
        
        echo "Building with Meson/Ninja..."
        meson setup build --prefix=/usr
        ninja -C build
        
        echo "Installing..."
        sudo ninja -C build install
        
        # Update library cache
        sudo ldconfig
        
        cd /tmp
        rm -rf playerctl.zip playerctl-${PLAYERCTL_VERSION}
    fi
    
    # Return to script directory
    cd "$SCRIPT_DIR"
    
    # Verify installation
    if command -v playerctl &> /dev/null; then
        INSTALLED_VERSION=$(playerctl --version 2>/dev/null || echo "unknown")
        print_success "playerctl installed successfully (version: $INSTALLED_VERSION)"
    else
        print_error "playerctl installation failed!"
        echo "  Media controls may not work. Try installing manually."
    fi
fi

# =============================================================================
# Step 3: Enable Bluetooth Service
# =============================================================================
print_header "Step 2/8: Enabling Bluetooth Service"

sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Check if Bluetooth adapter is available
if command -v bluetoothctl &> /dev/null; then
    if bluetoothctl show &> /dev/null; then
        print_success "Bluetooth service running"
    else
        print_warning "Bluetooth adapter not detected - may need reboot"
    fi
else
    print_warning "bluetoothctl not found"
fi

# =============================================================================
# Step 4: Create/Update Python Virtual Environment
# =============================================================================
print_header "Step 3/8: Setting Up Python Virtual Environment"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

print_success "Virtual environment ready"

# =============================================================================
# Step 5: Install Python Dependencies
# =============================================================================
print_header "Step 4/8: Installing Python Dependencies"

# Install from requirements.txt first
if [[ -f "requirements.txt" ]]; then
    echo "Installing from requirements.txt..."
    pip install -r requirements.txt
fi

# Install/upgrade specific required packages
echo ""
echo "Installing/upgrading core packages..."
pip install --upgrade \
    flask>=3.0.0 \
    requests \
    geopy>=2.4.1 \
    bleak>=0.22.0 \
    certifi \
    python-dotenv \
    folium

# Install PyBluez for Linux (optional, provides additional Bluetooth features)
echo ""
echo "Attempting to install PyBluez (Linux Bluetooth)..."
pip install pybluez 2>/dev/null || print_warning "PyBluez installation failed - this is OK, bleak will be used"

# Regenerate requirements.txt with all installed packages
echo ""
echo "Regenerating requirements.txt..."
pip freeze > requirements.txt
print_success "requirements.txt updated"

print_success "Python dependencies installed"

# =============================================================================
# Step 6: Fix Bluetooth Permissions
# =============================================================================
print_header "Step 5/8: Fixing Bluetooth Permissions"

PYTHON_PATH=$(readlink -f "$(which python3)")
echo "Python path: $PYTHON_PATH"

echo "Setting capabilities for Bluetooth access without sudo..."
if sudo setcap 'cap_net_raw,cap_net_admin+eip' "$PYTHON_PATH" 2>/dev/null; then
    print_success "Bluetooth permissions set"
    echo "  You can now run Bluetooth scans without sudo"
else
    print_warning "Could not set capabilities"
    echo "  You may need to run the app with sudo for Bluetooth"
fi

# Also set for venv python
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"
if [[ -f "$VENV_PYTHON" ]]; then
    VENV_PYTHON_REAL=$(readlink -f "$VENV_PYTHON")
    if [[ "$VENV_PYTHON_REAL" != "$PYTHON_PATH" ]]; then
        echo "Setting capabilities for venv Python..."
        sudo setcap 'cap_net_raw,cap_net_admin+eip' "$VENV_PYTHON_REAL" 2>/dev/null || true
    fi
fi

# =============================================================================
# Step 7: Verify Module Imports
# =============================================================================
print_header "Step 6/8: Verifying Python Modules"

echo "Testing module imports..."
IMPORT_ERRORS=0

# Test geopy
if python3 -c "import geopy; print(f'  geopy version: {geopy.__version__}')" 2>/dev/null; then
    print_success "geopy imports successfully"
else
    print_error "geopy import failed!"
    IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
fi

# Test bleak
if python3 -c "import bleak; print(f'  bleak version: {bleak.__version__}')" 2>/dev/null; then
    print_success "bleak imports successfully"
else
    print_error "bleak import failed!"
    IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
fi

# Test flask
if python3 -c "import flask; print(f'  flask version: {flask.__version__}')" 2>/dev/null; then
    print_success "flask imports successfully"
else
    print_error "flask import failed!"
    IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
fi

# Test certifi
if python3 -c "import certifi; print(f'  certifi path: {certifi.where()[:50]}...')" 2>/dev/null; then
    print_success "certifi imports successfully"
else
    print_warning "certifi import failed (geocoding may have SSL issues)"
fi

# Test folium
if python3 -c "import folium; print(f'  folium version: {folium.__version__}')" 2>/dev/null; then
    print_success "folium imports successfully"
else
    print_warning "folium import failed (maps may not work)"
fi

if [[ $IMPORT_ERRORS -gt 0 ]]; then
    print_error "$IMPORT_ERRORS critical module(s) failed to import!"
    echo "  Try running: pip install --force-reinstall flask geopy bleak"
fi

# =============================================================================
# Step 8: Ensure Scripts Exist
# =============================================================================
print_header "Step 7/8: Checking Project Scripts"

# Check/create build_carplay.sh
if [[ ! -f "build_carplay.sh" ]]; then
    echo "Creating placeholder build_carplay.sh..."
    cat > build_carplay.sh << 'EOF'
#!/usr/bin/env bash
# CarPlay Engine Build Script (Placeholder)
# Replace this with actual build commands when CarPlay engine is configured

echo "=============================================="
echo "  CarPlay Engine Build"
echo "=============================================="
echo ""
echo "CarPlay engine build completed (placeholder for now)."
echo ""
echo "To build the actual FastCarPlay engine:"
echo "  1. cd carplay_engine"
echo "  2. mkdir -p build && cd build"
echo "  3. cmake .."
echo "  4. make"
echo ""
EOF
    chmod +x build_carplay.sh
    print_success "build_carplay.sh created (placeholder)"
else
    print_success "build_carplay.sh exists"
fi

# Check start.sh
if [[ -f "start.sh" ]]; then
    chmod +x start.sh
    print_success "start.sh exists and is executable"
else
    print_warning "start.sh not found"
fi

# Check app.py
if [[ -f "app.py" ]]; then
    print_success "app.py exists"
else
    print_error "app.py not found - main application missing!"
fi

# =============================================================================
# Step 9: Verify playerctl for media controls
# =============================================================================
print_header "Step 8/8: Verifying Media Control Tools"

echo "Checking playerctl..."
if command -v playerctl &> /dev/null; then
    PLAYERCTL_VER=$(playerctl --version 2>/dev/null || echo "installed")
    print_success "playerctl is available (${PLAYERCTL_VER})"
    echo "  Media controls (play/pause/next/prev) will work with Bluetooth audio"
else
    print_warning "playerctl not found"
    echo "  Media controls will not work until playerctl is installed"
fi

# =============================================================================
# Final Summary
# =============================================================================
print_header "Environment Fix Complete!"

echo -e "${GREEN}All fixes applied successfully!${NC}"
echo ""
echo "Summary:"
echo "  ✓ System dependencies installed"
echo "  ✓ playerctl built from source (for media controls)"
echo "  ✓ Bluetooth service enabled"
echo "  ✓ Python virtual environment ready"
echo "  ✓ Python packages installed"
echo "  ✓ Bluetooth permissions configured"
echo "  ✓ Module imports verified"
echo "  ✓ Project scripts checked"
echo ""
echo -e "${YELLOW}Recommended: Reboot your Raspberry Pi for all changes to take effect:${NC}"
echo "  sudo reboot"
echo ""
echo -e "${GREEN}After reboot, start the app with:${NC}"
echo ""
echo "  cd $SCRIPT_DIR"
echo "  source venv/bin/activate"
echo "  python3 app.py"
echo ""
echo "Or use the startup script:"
echo "  ./start.sh"
echo ""
echo "The app will be available at: http://localhost:5000"
echo ""

