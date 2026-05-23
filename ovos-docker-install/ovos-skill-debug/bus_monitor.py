import time
from ovos_bus_client import MessageBusClient

print('Connecting to OVOS Message Bus...')
# Explicitly use 127.0.0.1 to match your container's log signature
bus = MessageBusClient(host="127.0.0.1", port=8181)

def on_hotword(message):
    print("\n[🔥 HOTWORD DETECTED] Engine captured the wake word!")
    print(f"Details: {message.get('data')}\n")

def on_listening(message):
    print("[🎤 LISTENING] OVOS is now actively recording your voice...")

def on_error(message):
    print(f"[⚠️ ERROR EVENT] {message.get('type')} -> {message.get('data')}")

# Register target handlers rather than a blanket '*' catch-all
print('Registering specific hotword and audio listeners...')
bus.on('recognizer_loop:wakeup', on_hotword)
bus.on('ovos.hotword.trigger', on_hotword)
bus.on('recognizer_loop:record_begin', on_listening)
bus.on('ovos.audio.speech.start', on_listening)

try:
    # Boot the connection engine
    bus.run_in_thread()
    print("Connection established. Waiting for handshake to settle...")
    time.sleep(2)
    
    print("\n--- Monitoring started! Speak your wake word ('Hey K9') now ---")
    print("Press Ctrl+C to stop.\n")
    
    while True:
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nClosing connection...")
    bus.close()
except Exception as e:
    print(f"Connection error: {e}")