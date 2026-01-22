from ovos_bus_client import MessageBusClient

TARGET_SKILL = "ovos-skill-date-time.openvoiceos"   # 👈 change this

bus = MessageBusClient(host="127.0.0.1", port=8181)
bus.run_in_thread()

def on_message(message):
    ctx = message.context or {}
    skill_id = ctx.get("skill_id")

    if skill_id == TARGET_SKILL:
        print(f"\n[{message.msg_type}]")
        print(message.serialize())

bus.on('*', on_message)

input(f"Listening for messages from {TARGET_SKILL}...\nPress Enter to exit.\n")

