#!/usr/bin/env bash
# =============================================================================
# Install playerctl from source
# =============================================================================
# This script builds and installs playerctl on Raspberry Pi OS where
# apt packages may not be available or have dependency conflicts.
#
# Usage:
#   chmod +x scripts/install_playerctl.sh
#   bash scripts/install_playerctl.sh
# =============================================================================

set -e

echo "=============================================="
echo "  Installing playerctl from source"
echo "=============================================="
echo ""

# Check if already installed
if command -v playerctl &> /dev/null; then
    CURRENT_VERSION=$(playerctl --version 2>/dev/null || echo "unknown")
    echo "playerctl is already installed (version: $CURRENT_VERSION)"
    echo "To reinstall, first run: sudo rm -f /usr/local/bin/playerctl"
    exit 0
fi

echo "Installing build dependencies..."
sudo apt-get update

# Install core build tools
sudo apt-get install -y \
    meson \
    ninja-build \
    pkg-config \
    git \
    wget \
    unzip

# Try to install GLib dev package (may fail due to repo conflicts)
echo ""
echo "Installing GLib development files..."
if ! sudo apt-get install -y libglib2.0-dev 2>/dev/null; then
    echo "ERROR: Cannot install libglib2.0-dev due to package conflicts."
    echo "       The BlueZ AVRCP fallback will be used instead."
    echo ""
    echo "To fix this manually, try:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get dist-upgrade"
    echo "  sudo apt-get install libglib2.0-dev"
    exit 1
fi

# Optional: GObject introspection (not required for basic functionality)
echo ""
echo "Attempting to install GObject introspection (optional)..."
sudo apt-get install -y libgirepository1.0-dev gobject-introspection 2>/dev/null || \
sudo apt-get install -y libgirepository-1.0-dev 2>/dev/null || \
echo "  GObject introspection not available - building without it"

# Download and build playerctl
VERSION="2.4.1"
cd /tmp

echo ""
echo "Downloading playerctl v${VERSION}..."
rm -rf playerctl.zip playerctl-${VERSION} 2>/dev/null || true
wget -q https://github.com/altdesktop/playerctl/archive/refs/tags/v${VERSION}.zip -O playerctl.zip

if [[ ! -f playerctl.zip ]]; then
    echo "ERROR: Failed to download playerctl"
    exit 1
fi

echo "Extracting..."
unzip -q playerctl.zip
cd playerctl-${VERSION}

echo "Configuring with Meson..."
# Disable introspection and gtk-doc to minimize dependencies
meson setup build --prefix=/usr -Dintrospection=false -Dgtk-doc=false

echo "Building with Ninja..."
ninja -C build

echo "Installing..."
sudo ninja -C build install

# Update library cache
sudo ldconfig

# Clean up
cd /tmp
rm -rf playerctl.zip playerctl-${VERSION}

echo ""
echo "=============================================="

# Verify installation
if command -v playerctl &> /dev/null; then
    INSTALLED_VERSION=$(playerctl --version 2>/dev/null || echo "unknown")
    echo "SUCCESS: playerctl installed (version: $INSTALLED_VERSION)"
    echo ""
    echo "Test with:"
    echo "  playerctl -l          # List available players"
    echo "  playerctl play-pause  # Toggle playback"
else
    echo "ERROR: playerctl did not install correctly"
    echo "       The BlueZ AVRCP fallback will be used instead."
    exit 1
fi

echo "=============================================="

