from ovos_bus_client.message import Message
from ovos_bus_client.client import MessageBusClient
import time
from threading import Thread

class Speak_behavior():

    def __init__(self):
        self.last_time = time.time()
          # Create a connection to the Mycroft message bus
        self.bus = MessageBusClient()
        global stop_loop
        # A flag to control the run_forever loop
        self.stop_loop = False
        # Give the thread a moment to connect
        time.sleep(2)
        # Start the bus client in a separate thread to prevent blocking
        bus_thread = Thread(target=self.run_bus)
        bus_thread.daemon = True # This ensures the thread exits when the main program does
        bus_thread.start()

    def run_bus(self):
        # Starts the message bus client in a separate thread.
        global stop_loop
        self.bus.run_forever()
        while not stop_loop:
            time.sleep(1)

    def say_text(self, text):
        """Function to send a speak message to the bus."""
        # Create a message to speak the text
        message = Message("speak", data={"utterance": text})
        # Send the message to the bus
        self.bus.emit(message)

    def close_bus(self):
        self.bus.close()

speak_behavior = Speak_behavior()
speak_behavior.say_text("I am K6")