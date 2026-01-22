from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message # <-- Import the Message class
from threading import Thread
import time

# Create a single instance of the bus client
bus = MessageBusClient()

# Start the client in a separate thread
def start_bus_loop():
    bus.run_forever()

# We only start the thread if the program is run directly
if __name__ == "__main__":
    bus_thread = Thread(target=start_bus_loop, daemon=True)
    bus_thread.start()
    print("OVOS bus client started. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bus.close()
        print("OVOS bus client shut down.")

# Provide a simple function to speak
def speak(text):
    # Corrected line: create a Message object
    print("ovosclient speak: " + text)
    msg = Message("speak", data={"utterance": text})
    print("ovosclient emit: " + text)
    bus.emit(msg)