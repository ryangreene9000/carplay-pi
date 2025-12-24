"""
Sense HAT Module
Handles all Sense HAT interactions including sensors and LED display
"""

try:
    from sense_hat import SenseHat
    SENSE_HAT_AVAILABLE = True
except ImportError:
    SENSE_HAT_AVAILABLE = False
    print("Warning: Sense HAT not available. Running in simulation mode.")

class SenseHATManager:
    def __init__(self):
        if SENSE_HAT_AVAILABLE:
            self.sense = SenseHat()
            self.sense.clear()
        else:
            self.sense = None
            print("Sense HAT running in simulation mode")
    
    def get_sensor_data(self):
        """Get current sensor readings"""
        if not SENSE_HAT_AVAILABLE or not self.sense:
            return {
                'temperature': 0,
                'humidity': 0,
                'pressure': 0,
                'orientation': {'pitch': 0, 'roll': 0, 'yaw': 0}
            }
        
        try:
            return {
                'temperature': round(self.sense.get_temperature(), 1),
                'humidity': round(self.sense.get_humidity(), 1),
                'pressure': round(self.sense.get_pressure(), 1),
                'orientation': self.sense.get_orientation()
            }
        except Exception as e:
            print(f"Error reading sensors: {e}")
            return {
                'temperature': 0,
                'humidity': 0,
                'pressure': 0,
                'orientation': {'pitch': 0, 'roll': 0, 'yaw': 0}
            }
    
    def update_display(self, system_state):
        """Update LED display based on system state"""
        if not SENSE_HAT_AVAILABLE or not self.sense:
            return
        
        try:
            # Show different patterns based on system state
            if system_state.get('music_playing'):
                # Show music note pattern (simple animation)
                self.sense.clear()
                # Simple pattern: alternating colors
                for x in range(8):
                    for y in range(8):
                        if (x + y) % 2 == 0:
                            self.sense.set_pixel(x, y, 0, 100, 200)
            elif system_state.get('bluetooth_connected'):
                # Show Bluetooth symbol pattern
                self.sense.clear()
                # Blue pattern
                for x in range(8):
                    for y in range(8):
                        if x < 4:
                            self.sense.set_pixel(x, y, 0, 0, 200)
            else:
                # Default: show temperature gradient
                temp = self.get_sensor_data()['temperature']
                # Map temperature to color (blue=cold, red=hot)
                r = min(255, max(0, int((temp - 15) * 10)))
                b = min(255, max(0, int((35 - temp) * 10)))
                self.sense.clear(r, 0, b)
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def show_message(self, message, scroll_speed=0.1):
        """Display scrolling message on LED matrix"""
        if not SENSE_HAT_AVAILABLE or not self.sense:
            print(f"Sense HAT message: {message}")
            return
        
        try:
            self.sense.show_message(message, scroll_speed=scroll_speed)
        except Exception as e:
            print(f"Error showing message: {e}")

