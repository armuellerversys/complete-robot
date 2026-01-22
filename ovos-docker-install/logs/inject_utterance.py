from ovos_bus_client import MessageBusClient
from ovos_bus_client.message import Message

bus = MessageBusClient(host="127.0.0.1", port=8181)
bus.run_in_thread()

text = "what time is it"

msg = Message(
    "recognizer_loop:utterance",
    data={
        "utterances": [text],
        "lang": "en-us"
    },
    context={
        "source": "fake-stt",
        "client": "tester"
    }
)

bus.emit(msg)

print(f"Injected utterance: {text}")

