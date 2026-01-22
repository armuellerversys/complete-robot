#!/usr/bin/env python3
"""
OVOS Skill Test Client
----------------------
Simulates a wakeword + utterance and captures spoken responses from OVOS.

Usage:
    python ovos_skill_test.py "what time is it"
"""

import json
import time
#import pyttsx3
import os
import sys
from datetime import datetime
from websocket import create_connection

# ========== Configuration ==========
BUS_URL = "ws://localhost:8181/core"
OUTPUT_DIR = "responses_audio"
WAKEWORD = "hey k6"
LANG = "en-us"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== Local TTS Setup ==========
#tts = pyttsx3.init()
#tts.setProperty("rate", 180)
#tts.setProperty("volume", 1.0)

def save_and_speak(text):
    """Save TTS output to WAV and play it locally."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"response_{timestamp}.wav")
    print(f"🔊 Speaking and saving to: {filename}")

    # Save synthesized voice
    #tts.save_to_file(text, filename)
    #tts.runAndWait()

    # Playback (optional)
    #try:
     #   import simpleaudio as sa
    #    wave_obj = sa.WaveObject.from_wave_file(filename)
    #    play_obj = wave_obj.play()
    #    play_obj.wait_done()
    #except ImportError:
    #    print("(⚠️ simpleaudio not installed, skipping playback)")

def emit(ws, event_type, data=None):
    """Emit a message to OVOS Message Bus."""
    msg = {
        "type": event_type,
        "data": data or {},
        "context": {"source": "test-client", "destination": None}
    }
    ws.send(json.dumps(msg))
    print(f"→ Sent: {event_type} -> {data}")

# ========== Main ==========
def main():
    if len(sys.argv) < 2:
        print("Usage: python ovos_skill_test.py \"<utterance>\"")
        sys.exit(1)

    utterance = sys.argv[1]
    print(f"\n🎙️  Testing utterance: \"{utterance}\"")
    print(f"Connecting to OVOS bus at {BUS_URL}...\n")

    ws = create_connection(BUS_URL)
    print("✅ Connected to OVOS Message Bus\n")

    # Simulate hotword trigger
    emit(ws, "recognizer_loop:wakeword", {"utterance": WAKEWORD, "session": "test"})
    time.sleep(1)

    # Send utterance
    emit(ws, "recognizer_loop:utterance", {"utterances": [utterance], "lang": LANG})

    print("\n🎧 Listening for OVOS responses (Ctrl+C to exit)\n")

    try:
        while True:
            message = ws.recv()
            msg = json.loads(message)
            mtype = msg.get("type")

            if mtype == "speak":
                text = msg["data"].get("utterance", "")
                print(f"🗣️ OVOS says: {text}")
                if text:
                    save_and_speak(text)

            elif mtype.startswith("enclosure.mouth.") or mtype.startswith("audio."):
                pass  # Skip display/audio events
            else:
                print("Event:", mtype)

    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user.")
    finally:
        ws.close()
        print("🔌 Disconnected from OVOS bus.")

if __name__ == "__main__":
    main()
