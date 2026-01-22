from ovos_pubsub import OvosPubSub
import time

def main():
    print("--- OVOS Messagebus Connectivity Test ---")
    
    # 1. Initialize the client
    # It will automatically use OVOS_BUS_HOST from your docker-compose
    bus = OvosPubSub()

    print("Sending 'speak' command...")
    
    # 2. Try to speak
    bus.say("The camera application has successfully connected to the message bus.")
    
    print("Message sent! Waiting 5 seconds to ensure delivery...")
    time.sleep(5)
    print("Test complete.")

if __name__ == "__main__":
    main()
