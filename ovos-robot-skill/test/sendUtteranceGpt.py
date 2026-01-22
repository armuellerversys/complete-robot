import json
import time
import traceback
import logging
from websocket import create_connection

# OVOS Message Bus URL (default)
BUS_URL = "ws://localhost:8181/core"
# BUS_URL = "http://192.168.4.6:6000/core"

try:
    # Connect to the OVOS message bus
    print(f"Connecting to OVOS bus at {BUS_URL}...")
    ws = create_connection(BUS_URL)
    print("Connected!")

    def emit(event_type, data=None):
        """Helper to send a message on the OVOS message bus."""
        msg = {
            "type": event_type,
            "data": data or {},
            "context": {
                "source": "test-client",
                "destination": None
            }
        }
        ws.send(json.dumps(msg))
        print(f"Sent: {event_type} -> {data}")

    # ---- Simulate Hotword Trigger ----
    emit("recognizer_loop:wakeword", {"utterance": "hey k6", "session": "test"})

    # Small delay before sending utterance
    time.sleep(1)

    # ---- Simulate Recognized Speech ----
    emit("recognizer_loop:utterance", {"utterances": ["Robot test rainbow"], "lang": "en-us"})

    # Optional: Listen for any responses (e.g., skill speech output)
    print("\nListening for responses (press Ctrl+C to stop):")
except Exception as e:
     logging.getLogger("test_Utterance").error(traceback.format_exc())
search = True
try:
    while search:
        message = ws.recv()
        # print(f"test_Utterance message received {message}")
        e_dict = json.loads(message)

        if e_dict["type"].startswith("speak"):
            print(f"Event: {e_dict["type"]} --> {e_dict["data"].get("utterance")}")
            search = False
        else:
            print("Event:", e_dict["type"])
            if e_dict["type"].startswith("recognizer_loop:wakeword"):
                print ("wakeword found")

except KeyboardInterrupt:
    print("\nClosing connection.")
finally:
    ws.close()

print("Skill test ok")