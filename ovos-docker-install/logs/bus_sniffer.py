from ovos_bus_client import MessageBusClient

bus = MessageBusClient(host="127.0.0.1", port=8181)
bus.run_in_thread()

def dump(message):
    print(message.serialize())

bus.on('*', dump)

input("Listening to OVOS messagebus. Press Enter to quit.\n")