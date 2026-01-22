import json
import time
import traceback
import logging
import sys
from datetime import datetime
from websocket import create_connection

# OVOS Message Bus URL (default)
BUS_URL = "ws://localhost:8181/core"

try:
    # Connect to the OVOS message bus
    print(f"Connecting to OVOS bus at {BUS_URL}...")
    ws = create_connection(BUS_URL)
    print("*********************** Connected! *********************")

    # Optional: Listen for any responses (e.g., skill speech output)
    print("\nListening for responses (press Ctrl+C to stop):")
except Exception as e:
     logging.getLogger("Receive Ovos event").error(traceback.format_exc())
     sys.exit(1)

try:
    while True:
        message = ws.recv()
        # print(f"test_Utterance message received {message}")
        current_time = datetime.now().strftime("%H:%M:%S")
        e_dict = json.loads(message)
        print(f"\n{current_time} Event -> {e_dict["type"]}")
       
except KeyboardInterrupt:
    print("\nReceive Ovos eventClosing connection.")
finally:
    ws.close()

print("\nReceive Ovos event test ok")