from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
import time
import os

COMMAND_FILE = "/home/ovos/python/voice-server/alternate/ovos_command.txt"

def main():
    """Main loop for the OVOS daemon."""
    print("OVOS daemon is starting...")
    bus = MessageBusClient()

    # The daemon needs to run forever to handle commands.
    bus.run_forever()

    while True:
        if os.path.exists(COMMAND_FILE):
            with open(COMMAND_FILE, "r") as f:
                command = f.read().strip()
            
            print(f"Daemon received command: '{command}'")

            # Execute the command
            if command.startswith("speak:"):
                text_to_speak = command.replace("speak:", "", 1)
                msg = Message("speak", data={"utterance": text_to_speak})
                bus.emit(msg)
                print(f"Emitted message to bus: '{text_to_speak}'")

            # Clean up the command file
            os.remove(COMMAND_FILE)
        
        # Poll for new commands every 0.1 seconds
        time.sleep(0.1)

if __name__ == "__main__":
    main()