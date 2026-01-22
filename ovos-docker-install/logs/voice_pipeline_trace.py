from ovos_bus_client import MessageBusClient
from datetime import datetime

bus = MessageBusClient(host="127.0.0.1", port=8181)
bus.run_in_thread()

PIPELINE = [
    "recognizer_loop:wakeword",
    "recognizer_loop:record_begin",
    "recognizer_loop:record_end",
    "recognizer_loop:utterance",
    "intent_service:intent",
    "mycroft.skill.start",
    "mycroft.skill.end",
    "speak"
]

def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def on_message(message):
    if message.msg_type not in PIPELINE:
        return

    ctx = message.context or {}
    skill = ctx.get("skill_id", "-")

    line = f"{ts()} | {message.msg_type:30} | skill={skill}"

    if message.msg_type == "recognizer_loop:utterance":
        line += f" | text={message.data.get('utterances')}"

    if message.msg_type == "intent_service:intent":
        line += f" | intent={message.data.get('intent_name')}"

    if message.msg_type == "speak":
        line += f" | speak={message.data.get('utterance')}"

    print(line)

bus.on('*', on_message)

input("\nTracing wakeword → STT → skill → speak\nPress Enter to stop.\n")

