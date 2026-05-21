from ovos_bus_client import MessageBusClient

print('Setting up client to connect to a local mycroft instance')
bus = MessageBusClient(host="localhost", port=8181)
## bus.run_in_thread()

def dump(message):
    print(message)

print('Registering handler for all messages...')

bus.on('*', dump)

input("Listening to OVOS messagebus. Press Enter to exit.\n")

bus.run_forever()