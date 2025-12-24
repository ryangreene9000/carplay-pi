import threading
import time
import logging
import subprocess
import requests
import os
import sys
import contextlib

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    sr = None
    logging.warning("SpeechRecognition not available. Voice control disabled.")

logging.basicConfig(level=logging.DEBUG)

class VoiceController:
    def __init__(self, api_base_url="http://localhost:5000"):
        if not SPEECH_RECOGNITION_AVAILABLE:
            raise ImportError("SpeechRecognition module not available. Install with: pip install SpeechRecognition PyAudio")
        
        # Suppress ALSA error messages
        self._suppress_alsa_errors()
        
        self.recognizer = sr.Recognizer()
        
        # Initialize microphone with stderr suppressed to avoid ALSA warnings
        # These warnings are harmless but annoying - they occur when PyAudio
        # enumerates audio devices and some devices don't exist
        with self._suppress_stderr():
            # Try to find USB microphone first, fallback to default
            mic_index = self._find_usb_microphone()
            if mic_index is not None:
                logging.info(f"Using USB microphone (device index {mic_index})")
                self.mic = sr.Microphone(device_index=mic_index)
            else:
                logging.info("Using default microphone")
                self.mic = sr.Microphone()
        
        self.active = False
        self.thread = None
        self.api_base_url = api_base_url
    
    def _suppress_alsa_errors(self):
        """Suppress ALSA error messages by setting environment variables"""
        # Set ALSA to use USB audio card if available
        os.environ.setdefault('ALSA_CARD', '2')  # USB audio device
        os.environ.setdefault('PULSE_ALSA_HACK_DEVICE', '1')
        # Suppress Python warnings
        import warnings
        warnings.filterwarnings('ignore', category=UserWarning)
    
    @staticmethod
    @contextlib.contextmanager
    def _suppress_stderr():
        """Context manager to suppress stderr (for ALSA warnings)"""
        # Save original stderr
        original_stderr = sys.stderr
        try:
            # Redirect stderr to /dev/null to suppress ALSA warnings
            sys.stderr = open(os.devnull, 'w')
            yield
        finally:
            # Restore original stderr
            sys.stderr.close()
            sys.stderr = original_stderr
    
    def _find_usb_microphone(self):
        """Find USB microphone device index"""
        try:
            with self._suppress_stderr():
                mic_list = sr.Microphone.list_microphone_names()
                for i, name in enumerate(mic_list):
                    if 'usb' in name.lower() or 'USB' in name:
                        return i
        except Exception as e:
            logging.debug(f"Could not enumerate microphones: {e}")
        return None

    def start_listening(self):
        if self.active:
            logging.debug("Voice control already active.")
            return

        self.active = True
        self.thread = threading.Thread(target=self.listen_loop, daemon=True)
        self.thread.start()
        logging.info("Voice control thread started.")

    def stop_listening(self):
        self.active = False
        logging.info("Voice control stopped.")

    def listen_loop(self):
        # Adjust for ambient noise once at start (suppress ALSA errors)
        try:
            logging.info("Adjusting for ambient noise...")
            with self._suppress_stderr():
                with self.mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logging.info("Ambient noise adjustment complete.")
        except Exception as e:
            logging.warning(f"Could not adjust for ambient noise: {e}. Continuing anyway...")
        
        while self.active:
            try:
                # Suppress ALSA errors during audio capture
                with self._suppress_stderr():
                    with self.mic as source:
                        logging.debug("Listening for voice command...")
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        logging.debug("Audio captured, processing...")

                text = self.recognizer.recognize_google(audio).lower()
                logging.info(f"Voice command heard: {text}")
                self.handle_command(text)

            except sr.WaitTimeoutError:
                # Normal timeout - just continue listening
                continue
            except sr.UnknownValueError:
                # Could not understand audio
                logging.debug("Could not understand audio")
                continue
            except sr.RequestError as e:
                # API was unreachable or unresponsive
                logging.error(f"Speech recognition API error: {e}")
                time.sleep(2)  # Wait before retrying
                continue
            except Exception as e:
                logging.error(f"Voice error: {e}")
                time.sleep(1)  # Brief pause before retrying
                continue

    def handle_command(self, text):
        logging.info(f"Processing voice command: '{text}'")
        try:
            if "play" in text:
                response = requests.post(f"{self.api_base_url}/api/media/play", timeout=5)
                if response.status_code == 200:
                    logging.info(f"Play command executed successfully")
                else:
                    logging.warning(f"Play command failed: {response.status_code}")
            elif "pause" in text:
                response = requests.post(f"{self.api_base_url}/api/media/pause", timeout=5)
                if response.status_code == 200:
                    logging.info(f"Pause command executed successfully")
                else:
                    logging.warning(f"Pause command failed: {response.status_code}")
            elif "next" in text or "skip" in text:
                response = requests.post(f"{self.api_base_url}/api/media/next", timeout=5)
                if response.status_code == 200:
                    logging.info(f"Next command executed successfully")
                else:
                    logging.warning(f"Next command failed: {response.status_code}")
            elif "back" in text or "previous" in text:
                response = requests.post(f"{self.api_base_url}/api/media/previous", timeout=5)
                if response.status_code == 200:
                    logging.info(f"Previous command executed successfully")
                else:
                    logging.warning(f"Previous command failed: {response.status_code}")
            else:
                logging.debug(f"Unrecognized voice command: '{text}'")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error calling media API: {e}")
        except Exception as e:
            logging.error(f"Error executing command: {e}")
