from ovos_bus_client.message import Message
from ovos_bus_client.client import MessageBusClient
import time
import sys
from threading import Thread

if len(sys.argv) < 3:
    print("Usage: python my_script.py <arg1> <arg2>")
    sys.exit(1)

text = sys.argv[1]
arg = sys.argv[2]
# Create a connection to the Mycroft message bus
bus = MessageBusClient()
global stop_loop
# A flag to control the run_forever loop
stop_loop = False

def run_bus():
    """Starts the message bus client in a separate thread."""
    global stop_loop
    bus.run_forever()
    while not stop_loop:
        time.sleep(1)

def say_text(text):
    """Function to send a speak message to the bus."""
    # Create a message to speak the text
    message = Message("speak", data={"utterance": text})
    # Send the message to the bus
    bus.emit(message)

# Start the bus client in a separate thread to prevent blocking
bus_thread = Thread(target=run_bus)
bus_thread.daemon = True # This ensures the thread exits when the main program does
bus_thread.start()

# Give the thread a moment to connect
time.sleep(2)

# The text you want to speak
## my_text = "This is a simple text to speech test."

print(f"Attempting to speak: '{text}'")

# Call the function to make OVOS speak
say_text(text)

# Wait for a moment for the audio to play
time.sleep(5)

# Signal the thread to stop and close the bus

stop_loop = True
bus.close()

print("Program finished.")