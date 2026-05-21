from ovos_bus_client import MessageBusClient

print('Setting up client to connect to a local mycroft instance')
bus = MessageBusClient(host="localhost", port=8181)

def print_utterance(message):
    print('OVOS said "{}"'.format(message.data.get('utterance')))

print('Registering handler for speak message...')

bus.on('speak', print_utterance)

input("Listening to OVOS messagebus. Press Enter to exit.\n")

bus.run_forever()