from ovos_bus_client import MessageBusClient, Message
import time
import sys

# --- Configuration ---
HOST = "127.0.0.1"
PORT = 8181
TEST_UTTERANCE = "Robot test rainbow"
TIMEOUT = 40 # Seconds to wait for a response

#import debugpy
#debugpy.listen(('0.0.0.0', 5678))

#input('Hello! Start sendUtteranceGemini\n')

# Global flag and container to capture the response
response_received = False
skill_response = None

def handle_speak_message(message):
    """
    Handler function that runs when a 'speak' message is received on the bus.
    """
    global response_received, skill_response
    
    # The 'speak' message contains the text that OVOS will say.
    utterance = message.data.get('utterance', 'No utterance found')
    print('OVOS said "{}"'.format(message.data.get('utterance')))
    print("*****************************************************")
    print(f"✅ Enter handle_speak_message -> {utterance} --> {message.data}")
    # We only care about the response to our utterance, not other chatter
    if utterance and "time" in utterance.lower():
        skill_response = utterance
        response_received = True
        print(f"\n📢 **SKILL RESPONSE RECEIVED:**\n   Text: {skill_response}")
        # Optionally, you can stop the client immediately here if you know your skill is fast
        # client.stop() 

def handle_speak_wakeword(message):
    print("Event handle speak wakeword catched")

def send_test_and_listen():
    """
    Sets up the listener, sends the test message, and waits for a response.
    """
    global response_received, skill_response
    
    print(f"Connecting to OVOS Message Bus at ws://{HOST}:{PORT}...")
    client = MessageBusClient(host=HOST, port=PORT)
    
    # 1. Register the handler function for 'speak' messages
    client.on('speak', handle_speak_message)
    client.on('recognizer_loop:wakeword', handle_speak_wakeword)
    
    # Start the client thread to allow sending/receiving messages concurrently
    client.run_in_thread()
    time.sleep(1) # Wait for connection

    print("✅ Connection attempt complete. Listener active for 'speak' messages.")

    print("✅ Connection established. Listener active for 'speak' messages.")
    
    # 2. Send the test utterance
    message_type = "recognizer_loop:utterance"
    message_data = {
        "utterances": [TEST_UTTERANCE],
        "lang": "en-us"
    }
    
    test_message = Message(message_type, data=message_data)
    print(f"\n➡️ Sending test utterance: '{TEST_UTTERANCE}'")
    client.emit(test_message)

    # 3. Wait for the response
    start_time = time.time()
    while not response_received and (time.time() - start_time) < TIMEOUT:
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(0.5)

    print("\n--- Test Complete ---")
    
    if skill_response:
        print("✅ **Test Result: SUCCESS**")
        print(f"   Response captured: **{skill_response}**")
    else:
        print("❌ **Test Result: FAILURE**")
        print(f"   No 'speak' response received from the Date/Time skill within {TIMEOUT} seconds.")

    # Clean up the client connection
    client.close()

if __name__ == "__main__":
    try:
        send_test_and_listen()
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")