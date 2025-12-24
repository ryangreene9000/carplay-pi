# Apple CarPlay-Style Infotainment System for Raspberry Pi

> **Note:** This is a CarPlay-**style** UI inspired by Apple CarPlay. This is **not** an official Apple CarPlay implementation, and is not affiliated with or endorsed by Apple Inc.

A custom embedded infotainment system built for Raspberry Pi 5, featuring a CarPlay-inspired touchscreen interface, Bluetooth audio streaming, turn-by-turn navigation, and real-time sensor monitoring. Built with Python/Flask and designed for seamless integration into vehicles without native smartphone integration.

## 🎯 Project Overview

This project solves the problem of outdated vehicle infotainment systems by providing a modern, cost-effective alternative. Many older vehicles lack smartphone integration features like Apple CarPlay or Android Auto, leaving drivers with limited navigation, music, and hands-free capabilities.

**Key Value Proposition:**
- Brings modern infotainment to older vehicles at a fraction of the cost of aftermarket head units
- Modular software architecture for easy customization and extension
- Seamless Bluetooth audio integration with existing vehicle speakers
- Real-time GPS navigation with turn-by-turn directions

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────┐
│         Raspberry Pi 5 (Host)               │
│  ┌──────────────────────────────────────┐  │
│  │     Flask Web Server (Backend)       │  │
│  │  - REST API endpoints                │  │
│  │  - Bluetooth/Media control           │  │
│  │  - GPS/Navigation logic              │  │
│  │  - Sensor data aggregation           │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │   Web UI (Frontend)                  │  │
│  │  - Touchscreen interface             │  │
│  │  - Map visualization                 │  │
│  │  - Music controls                    │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
           │              │              │
           ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  Phone   │   │  Sense   │   │ Touch    │
    │ (BT A2DP)│   │   HAT    │   │ Screen   │
    └──────────┘   └──────────┘   └──────────┘
```

## 🛠️ Technical Stack

### Backend
- **Python 3.11+** - Core application logic
- **Flask** - Web framework and REST API
- **BlueZ/Bluetooth LE** - Audio streaming and device management
- **Google Maps API** - Geocoding, directions, places search
- **Geopy** - Additional geocoding support
- **Folium** - Interactive map rendering

### Frontend
- **HTML5/CSS3** - Responsive touchscreen UI
- **JavaScript (ES6+)** - Client-side interactivity
- **Leaflet.js** - Open-source mapping library
- **Web APIs** - Geolocation, Media Session

### Hardware Integration
- **Raspberry Pi 5** - Single-board computer
- **Sense HAT** - Environmental sensors (temperature, humidity, pressure)
- **7" Touchscreen Display** - Capacitive touch interface
- **Bluetooth** - A2DP audio sink, HFP for phone calls

## ✨ Key Features

### 🎵 Music Playback & Bluetooth Audio
- Stream music wirelessly from any smartphone
- Native BlueZ AVRCP control (play/pause/skip)
- Playerctl fallback for additional media players
- Real-time track metadata display

### 🗺️ Navigation Interface
- Turn-by-turn directions via Google Directions API
- Interactive map with route visualization
- Points of Interest (POI) search (gas stations, restaurants, etc.)
- Multiple location sources:
  - WiFi-based Google Geolocation (~20-50m accuracy)
  - GPS (if available)
  - IP geolocation fallback

### 📱 iPhone/Android Integration
- Web-based GPS bridge for iPhone (Safari geolocation API)
- Bluetooth Hands-Free Profile (HFP) for phone calls
- Google Maps URL sharing from phone to Pi
- Real-time location sync

### 📊 Sensor Monitoring
- Real-time environmental data (temperature, humidity, pressure)
- LED matrix visualization on Sense HAT
- System status display

### 🎙️ Voice Control (Optional)
- Speech recognition for hands-free operation
- Voice commands for navigation and media control

## 📁 Project Structure

```
carplay-pi/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
│
├── backend/                 # Flask backend application
│   ├── app.py              # Main Flask application
│   ├── modules/            # Application modules
│   │   ├── bluetooth_module.py
│   │   ├── music_module.py
│   │   ├── map_module.py
│   │   ├── sense_hat_module.py
│   │   ├── google_maps.py
│   │   ├── geolocation.py
│   │   └── ...
│   └── test_voice.py       # Voice control testing
│
├── frontend/               # Web UI
│   ├── templates/          # HTML templates
│   │   ├── main_menu.html
│   │   ├── music.html
│   │   ├── map.html
│   │   └── ...
│   └── static/             # Static assets
│       ├── css/
│       └── js/
│
├── hardware/               # Hardware-specific code
│   └── carplay_engine/    # External CarPlay decoder (if used)
│
├── config/                 # Configuration
│   └── config.example.py  # Configuration template
│
└── scripts/                # Setup and utility scripts
    ├── setup_rpi_bluetooth.sh
    ├── install_playerctl.sh
    ├── run_car_stereo.sh
    └── ...
```

## 🚀 Getting Started

### Prerequisites

**Hardware:**
- Raspberry Pi 5
- Sense HAT (optional, for sensor data)
- 7" Touchscreen Display
- MicroSD card (32GB+ recommended)
- Power supply (5V 5A USB-C)

**Software:**
- Raspberry Pi OS (latest version)
- Python 3.11+
- Bluetooth support (BlueZ)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ryangreene9000/carplay-pi.git
   cd carplay-pi
   ```

2. **Set up configuration:**
   ```bash
   cp config/config.example.py config/config.py
   # Edit config/config.py and add your Google Maps API key
   ```

3. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-venv bluetooth bluez \
       pulseaudio pulseaudio-module-bluetooth
   ```

4. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Set up Bluetooth (if needed):**
   ```bash
   bash scripts/setup_rpi_bluetooth.sh
   ```

### Running Locally

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Set environment variables (optional):**
   ```bash
   export GOOGLE_MAPS_API_KEY="your-api-key-here"
   export FLASK_SECRET_KEY="your-secret-key-here"
   ```

3. **Run the application:**
   ```bash
   python backend/app.py
   ```

4. **Access the interface:**
   - On Raspberry Pi: `http://localhost:5000`
   - From network: `http://<pi-ip-address>:5000`

### Configuration

**Google Maps API Setup:**

1. Get an API key from [Google Cloud Console](https://console.cloud.google.com/google/maps-apis)
2. Enable the following APIs:
   - Maps JavaScript API
   - Directions API
   - Places API
   - Geocoding API
   - Geolocation API
3. Add the key to `config/config.py` or set `GOOGLE_MAPS_API_KEY` environment variable

**Bluetooth Setup:**

The system supports two methods for Bluetooth audio:

1. **A2DP Sink** - Pi receives audio from phone
   ```bash
   bash scripts/setup_rpi_bluetooth.sh
   ```

2. **Media Control** - Control playback on connected phone
   ```bash
   bash scripts/install_playerctl.sh
   ```

## 📸 Screenshots

> **Note:** Screenshots can be added here. Consider including:
> - Main menu interface
> - Navigation screen with route
> - Music player with track info
> - Settings screen

## 🔧 Hardware Notes

### Raspberry Pi 5
- Recommended: 4GB+ RAM
- USB-C power supply (5V 5A)
- MicroSD card (Class 10, 32GB+)
- WiFi/Bluetooth on-board

### Touchscreen Display
- 7" capacitive touchscreen
- HDMI connection for video
- USB for touch input
- Recommended resolution: 1024x600 or higher

### Sense HAT
- I2C connection required
- Enable I2C in `raspi-config`
- Provides environmental sensors and LED matrix

### Audio
- Options: HDMI audio, 3.5mm analog, or Bluetooth
- Configure via PulseAudio
- Test audio: `speaker-test -t sine -f 1000`

## 🔒 Security

**Important:** API keys and secrets are intentionally excluded from this repository.

- **Never commit `config/config.py`** - It's in `.gitignore`
- Use environment variables for production deployments
- API keys should be injected via CI/CD or environment configuration
- Review `.gitignore` to ensure no secrets are tracked

## 🧪 Development

### Running Tests

```bash
# Voice control testing
python backend/test_voice.py
```

### Development on macOS

The codebase supports cross-platform development:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python backend/app.py
# Access at http://localhost:5001 (macOS uses 5001 to avoid AirPlay)
```

## 📝 API Documentation

### Key Endpoints

- `GET /` - Main menu
- `GET /music` - Music player screen
- `GET /map` - Navigation screen
- `GET /api/status` - System status
- `POST /api/media/play` - Play media
- `POST /api/media/pause` - Pause media
- `GET /api/location/current` - Get current location
- `POST /api/navigation/set` - Set navigation destination

See code comments for complete API documentation.

## 🛣️ Roadmap

Potential future enhancements:
- [ ] Official Android Auto integration
- [ ] Spotify API direct playback
- [ ] Offline map caching
- [ ] Custom app/plugin system
- [ ] Voice assistant integration
- [ ] OBD-II data display

## 🤝 Contributing

This is a personal project, but suggestions and feedback are welcome!

## 📄 License

This project is for educational and personal use.

## 👤 Author

**Ryan Greene**
- Portfolio: [ryangreenedev.com](https://ryangreenedev.com)
- GitHub: [@ryangreene9000](https://github.com/ryangreene9000)

## 🙏 Acknowledgments

- [CarPlay Engine](https://github.com/eav01/carplay) - External CarPlay decoder library
- OpenStreetMap contributors
- Leaflet.js mapping library
- Raspberry Pi Foundation

---

**Disclaimer:** This project is not affiliated with, endorsed by, or connected to Apple Inc. "CarPlay" is a trademark of Apple Inc. This is an independent project that provides a CarPlay-style user interface for educational purposes.
