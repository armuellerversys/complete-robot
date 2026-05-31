
from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
import time
import logging

class SoundServer():

    def __init__(self):
        self.logger = SoundServer.getLogger("SoundServer")
        self.client = MessageBusClient()
        self.client.run_in_thread()
        time.sleep(1)
        self.client.connected_event.wait()

    def play_sound(self):
        self.logger.info("Enter play_sound...")
        if not self.client:
            self.logger.warning("Client not ready, skipping sound")
            return

        sound_path = "/home/ovos/.config/mycroft/boing_x.wav"
        self.logger.info(f"Sound path: {sound_path}")
        self.client.emit(
            Message(
                "mycroft.audio.play_sound",
                {"uri": sound_path}
            )
        )

    @staticmethod
    def getLogger(name):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # CHECK if logger already has handlers before adding a new one
        if not logger.handlers: 
            # create console handler with a higher log level
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            
            # create formatter and add it to the handlers
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
            ch.setFormatter(formatter)
            
            # add the handler to the logger
            logger.addHandler(ch)
            
        return logger

sound_server = SoundServer()
sound_server.play_sound()