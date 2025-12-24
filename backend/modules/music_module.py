"""
Music Module
Handles music playback via Bluetooth or local files
Supports Spotify integration (optional)
"""

import subprocess
import os

class MusicManager:
    def __init__(self):
        self.is_playing = False
        self.current_volume = 50
        self.player_process = None
        
        # Try to initialize audio system
        self._init_audio()
    
    def _init_audio(self):
        """Initialize audio system"""
        try:
            # Set default audio sink (for Bluetooth or local audio)
            # This may need adjustment based on your audio setup
            subprocess.run(['pactl', 'set-default-sink', '0'], check=False)
        except Exception as e:
            print(f"Audio init warning: {e}")
    
    def play(self, source='bluetooth'):
        """Start music playback"""
        try:
            if source == 'bluetooth':
                # For Bluetooth audio, the connection handles playback
                # We just need to ensure audio routing is correct
                self.is_playing = True
                return {'success': True, 'message': 'Playing via Bluetooth'}
            else:
                # For local file playback, you could use mpg123, vlc, etc.
                self.is_playing = True
                return {'success': True, 'message': 'Playing local file'}
        except Exception as e:
            print(f"Play error: {e}")
            return {'success': False, 'message': str(e)}
    
    def pause(self):
        """Pause music playback"""
        try:
            # For Bluetooth, pause might not be directly controllable
            # This would depend on the source device
            self.is_playing = False
            return {'success': True, 'message': 'Paused'}
        except Exception as e:
            print(f"Pause error: {e}")
            return {'success': False, 'message': str(e)}
    
    def stop(self):
        """Stop music playback"""
        try:
            if self.player_process:
                self.player_process.terminate()
                self.player_process = None
            self.is_playing = False
            return {'success': True, 'message': 'Stopped'}
        except Exception as e:
            print(f"Stop error: {e}")
            return {'success': False, 'message': str(e)}
    
    def set_volume(self, volume):
        """Set volume level (0-100)"""
        try:
            volume = max(0, min(100, volume))
            self.current_volume = volume
            
            # Convert to pulseaudio volume (0-65536)
            pa_volume = int((volume / 100) * 65536)
            
            # Set volume using pactl
            subprocess.run(
                ['pactl', 'set-sink-volume', '@DEFAULT_SINK@', str(pa_volume)],
                check=False
            )
            
            return {'success': True, 'message': f'Volume set to {volume}%'}
        except Exception as e:
            print(f"Volume set error: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_current_track(self):
        """Get information about currently playing track"""
        # This would need integration with the actual audio source
        # For Bluetooth, this is difficult without additional protocols
        return {
            'title': 'Unknown',
            'artist': 'Unknown',
            'album': 'Unknown'
        }

