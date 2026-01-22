from ovos_bus_client import MessageBusClient
from ovos_bus_client.message import Message
import time

bus = MessageBusClient(host="127.0.0.1", port=8181)
bus.run_in_thread()

# Fake wakeword
bus.emit(Message(
    "recognizer_loop:wakeword",
    data={"wakeword": "hey ovos"},
    context={"source": "fake"}
))

time.sleep(0.1)

# Fake mic open
bus.emit(Message(
    "recognizer_loop:record_begin",
    context={"source": "fake"}
))

time.sleep(0.5)

# Fake STT result
bus.emit(Message(
    "recognizer_loop:utterance",
    data={
        "utterances": ["what time is it"],
        "lang": "en-us"
    },
    context={"source": "fake"}
))

# Fake mic close
bus.emit(Message(
    "recognizer_loop:record_end",
    context={"source": "fake"}
))

print("Injected full wakeword → STT pipeline")

