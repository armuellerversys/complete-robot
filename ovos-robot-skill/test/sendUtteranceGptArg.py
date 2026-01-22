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

    search = True
    try:
        while search:
            message = ws.recv()
            # print(f"test_Utterance message received {message}")
            e_dict = json.loads(message)

            if e_dict["type"].startswith("speak"):
                print("Skill says:", e_dict["data"].get("utterance"))
                search = False
            else:
                print("Event:", e_dict["type"])
                if e_dict["type"].startswith("recognizer_loop:wakeword"):
                    print ("wakeword found")
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user.")
    finally:
        ws.close()
        print("🔌 Disconnected from OVOS bus.")

if __name__ == "__main__":
    main()
