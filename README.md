# Car Stereo System for Raspberry Pi 5

A comprehensive car stereo system built for Raspberry Pi 5 with Sense HAT and 7" touch screen display.

## Features

- 🎵 **Music Player**: Bluetooth audio streaming and local file playback
- 🗺️ **Navigation**: Interactive map with route planning using OpenStreetMap
- 📱 **Android Auto**: Integration support for Android Auto (requires OpenAuto)
- ⚙️ **Settings**: System configuration and sensor monitoring
- 📊 **Sense HAT Integration**: Real-time sensor data display and LED matrix visualization

## Hardware Requirements

- Raspberry Pi 5
- Sense HAT
- 7" Touch Screen Display
- Bluetooth adapter (if not built-in)
- Audio output (HDMI, 3.5mm, or Bluetooth)

## Software Requirements

- Raspberry Pi OS (latest version)
- Python 3.11+
- Bluetooth support (bluez)
- Audio system (PulseAudio or ALSA)

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /home/cqb5990/car_stereo_system
   ```

2. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-venv bluetooth bluez pulseaudio
   ```

3. **Create and activate virtual environment (required on newer Raspberry Pi OS):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Note:** If you encounter issues with Sense HAT, you may need to install system packages:
   ```bash
   sudo apt-get install sense-hat
   ```
   The application will run in simulation mode if Sense HAT hardware is not available.

5. **Set up Bluetooth (if needed):**
   ```bash
   sudo systemctl enable bluetooth
   sudo systemctl start bluetooth
   ```

## Running the Application

1. **Activate virtual environment (required):**
   ```bash
   cd /home/cqb5990/car_stereo_system
   source venv/bin/activate
   ```

2. **Run the application:**
   ```bash
   python3 app.py
   ```
   
   **Or use the startup script:**
   ```bash
   ./start.sh
   ```

3. **Access the interface:**
   - Open a web browser on the Raspberry Pi
   - Navigate to: `http://localhost:5000`
   - Or from another device on the same network: `http://<raspberry-pi-ip>:5000`

## Auto-Start on Boot (Optional)

To make the application start automatically when the Raspberry Pi boots:

1. **Create a systemd service file:**
   ```bash
   sudo nano /etc/systemd/system/car-stereo.service
   ```

2. **Add the following content (adjust paths as needed):**
   ```ini
   [Unit]
   Description=Car Stereo System
   After=network.target bluetooth.service

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/cqb5990/car_stereo_system
   ExecStart=/home/cqb5990/car_stereo_system/venv/bin/python3 /home/cqb5990/car_stereo_system/app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start the service:**
   ```bash
   sudo systemctl enable car-stereo.service
   sudo systemctl start car-stereo.service
   ```

## Configuration

### Audio Output
- Default audio output can be changed in Settings
- Options: Bluetooth, HDMI, Analog (3.5mm)
- Use `pactl list sinks` to see available audio outputs

### Bluetooth Devices
- Scan for devices from the Music screen
- Connect to your phone or audio device
- Audio will automatically route through Bluetooth when connected

### Bluetooth Audio Requirements (A2DP Sink)

For the Raspberry Pi to receive audio from your phone (act as an A2DP sink), install these packages:

```bash
sudo apt-get install -y bluez bluez-tools pulseaudio pulseaudio-module-bluetooth
```

**Important notes:**
- The Raspberry Pi must be configured as an A2DP audio sink
- Your phone acts as the A2DP source (sends audio to the Pi)
- Pairing may require confirmation on both devices

**To make the Pi discoverable for pairing:**
```bash
bluetoothctl
# Then in bluetoothctl:
power on
discoverable on
pairable on
agent on
default-agent
# Wait for your phone to find "raspberrypi" and pair
```

After pairing, PulseAudio should automatically route audio from the connected phone.

### Media Control Setup (play/pause/next/previous)

The app supports two methods for controlling phone media playback:

**Option A: playerctl (recommended)**
```bash
bash scripts/install_playerctl.sh
```

**Option B: BlueZ AVRCP via D-Bus (automatic fallback)**
```bash
pip install dbus-python
```

**Note:** If playerctl is not available or fails, the app automatically falls back to native BlueZ AVRCP control via D-Bus. No configuration needed - it just works!

### Map Location
- Default map location is set to Toronto, Canada
- Edit `modules/map_module.py` to change default location
- The map will try to use your current location if GPS is available

## Android Auto Setup

For full Android Auto functionality, you'll need to install OpenAuto or a similar solution:

1. **Install OpenAuto (example):**
   - Visit: https://github.com/f1xpl/openauto
   - Follow their installation instructions

2. **Update the path in `modules/android_auto_module.py`:**
   - Set `self.auto_executable` to the path of your Android Auto executable

## Troubleshooting

### Sense HAT Not Detected
- Ensure Sense HAT is properly connected
- Check I2C is enabled: `sudo raspi-config` → Interface Options → I2C
- The application will run in simulation mode if Sense HAT is not available

### Bluetooth Issues
- Ensure Bluetooth service is running: `sudo systemctl status bluetooth`
- Check if devices are discoverable
- Some devices may require pairing before connection

### Audio Not Working
- Check audio output: `pactl list sinks`
- Set default sink: `pactl set-default-sink <sink-name>`
- Test audio: `speaker-test -t sine -f 1000`

### Touch Screen Not Responsive
- Ensure touch screen drivers are installed
- Check touch screen calibration
- Use a modern browser (Chromium recommended)

## Project Structure

```
car_stereo_system/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── modules/              # Application modules
│   ├── sense_hat_module.py
│   ├── bluetooth_module.py
│   ├── music_module.py
│   ├── map_module.py
│   └── android_auto_module.py
├── templates/            # HTML templates
│   ├── main_menu.html
│   ├── music.html
│   ├── map.html
│   ├── android_auto.html
│   └── settings.html
└── static/               # Static files
    ├── css/
    │   └── main.css
    ├── js/
    │   ├── main.js
    │   ├── music.js
    │   ├── map.js
    │   ├── android_auto.js
    │   └── settings.js
    └── images/
```

## Cross-Platform Development

This codebase runs on **both macOS (for development) and Raspberry Pi (for the car)**:

| Platform | Bluetooth Backend | Setup Required |
|----------|------------------|----------------|
| macOS    | CoreBluetooth    | None (works automatically) |
| Raspberry Pi / Linux | BlueZ | Run `scripts/setup_rpi_bluetooth.sh` |
| Windows  | WinRT            | Usually works automatically |

### Developing on macOS

1. Clone the repo and create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run the Flask app:
   ```bash
   python3 app.py
   ```

3. Access at `http://localhost:5001` (macOS uses port 5001 to avoid AirPlay conflicts)

4. Bluetooth scanning works automatically via CoreBluetooth - no extra setup needed.

### Running on Raspberry Pi

**Recommended: Use the full setup script:**
```bash
cd ~/car_stereo_system
bash fix_rpi_environment.sh
sudo reboot
```

This script handles everything: system dependencies, Bluetooth, Python venv, and all packages.

**If you have dependency errors, do a clean reinstall:**
```bash
cd ~/car_stereo_system
rm -rf venv
bash fix_rpi_environment.sh
sudo reboot
```

**Manual setup (alternative):**

1. **Run the Bluetooth setup script** (first time only):
   ```bash
   chmod +x scripts/setup_rpi_bluetooth.sh
   bash scripts/setup_rpi_bluetooth.sh
   sudo reboot
   ```

2. **Verify Bluetooth is working**:
   ```bash
   bluetoothctl show      # Should list your adapter
   bluetoothctl scan on   # Test scanning (Ctrl+C to stop)
   ```

3. **Create virtual environment and install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Start the Flask app**:
   ```bash
   python3 app.py
   # Or use the startup script:
   ./start.sh
   ```

5. Access at `http://localhost:5000` or `http://<pi-ip>:5000`

## Development Notes

- The application uses Flask for the web interface
- All modules are designed to work in simulation mode if hardware is unavailable
- The interface is optimized for touch screens (7" display)
- Responsive design works on various screen sizes
- Bluetooth uses the `bleak` library for cross-platform BLE support

## Future Enhancements

- Spotify API integration for direct Spotify playback
- GPS module integration for accurate location tracking
- Voice control support
- CarPlay integration (more complex)
- Local music library management
- Equalizer and audio effects

## License

This project is for educational purposes.

## Support

For issues or questions, check the troubleshooting section or review the code comments.

