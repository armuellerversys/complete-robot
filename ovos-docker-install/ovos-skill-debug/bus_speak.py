from ovos_bus_client import MessageBusClient, Message

client = MessageBusClient()
client.run_in_thread()
client.connected_event.wait()

client.emit(Message('speak', data={'utterance': 'Hello this is a test of the speak message'}))