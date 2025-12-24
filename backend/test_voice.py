#!/usr/bin/env python3
"""Test script for voice control diagnostics"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("Voice Control Diagnostic Test")
print("=" * 50)

# Test 1: Check imports
print("\n1. Testing imports...")
try:
    import speech_recognition as sr
    print("   ✓ SpeechRecognition imported")
except ImportError as e:
    print(f"   ✗ SpeechRecognition import failed: {e}")
    sys.exit(1)

try:
    import pyaudio
    print("   ✓ PyAudio imported")
except ImportError as e:
    print(f"   ✗ PyAudio import failed: {e}")
    sys.exit(1)

# Test 2: Check microphone
print("\n2. Testing microphone...")
try:
    r = sr.Recognizer()
    m = sr.Microphone()
    print(f"   ✓ Microphone object created: {m}")
    
    mic_list = sr.Microphone.list_microphone_names()
    print(f"   ✓ Found {len(mic_list)} microphones:")
    for i, name in enumerate(mic_list[:5]):
        print(f"      {i}: {name}")
except Exception as e:
    print(f"   ✗ Microphone test failed: {e}")
    sys.exit(1)

# Test 3: Check VoiceController import
print("\n3. Testing VoiceController...")
try:
    from modules.voice_control import VoiceController
    print("   ✓ VoiceController imported")
    
    vc = VoiceController()
    print("   ✓ VoiceController initialized")
except Exception as e:
    print(f"   ✗ VoiceController failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Check API connectivity
print("\n4. Testing API connectivity...")
try:
    import requests
    response = requests.get("http://localhost:5000/api/status", timeout=2)
    if response.status_code == 200:
        print("   ✓ Flask API is accessible")
    else:
        print(f"   ⚠ Flask API returned status {response.status_code}")
except Exception as e:
    print(f"   ✗ Cannot reach Flask API: {e}")
    print("      Make sure the Flask app is running")

print("\n" + "=" * 50)
print("Diagnostic test complete!")
print("=" * 50)

