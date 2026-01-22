from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
import time
import logging


class OvosPubSub:
    def __init__(self, host="ovos_messagebus", port=8181, ssl=False, autoconnect=True):
        self.logger = self.getLogger("OvosPubSub")
        self.logger.debug(f"Connect to Messagebus {host} , Port: {port}")
        self.client = MessageBusClient(host=host, port=port, ssl=ssl)

        if autoconnect:
            self.connect()
        self.last_speak_time = time.time() - 6.0

    def connect(self):
        """Start the client in a background thread."""
        self.client.run_in_thread()
        time.sleep(0.3)  # give connection time

    # ----------------------------------------------------------------------
    # SUBSCRIBE (LISTEN)
    # ----------------------------------------------------------------------
    def listen_for_utterances(self):
        """
        Subscribe to spoken utterances coming from the STT engine.
        Message type: "recognizer_loop:utterance"
        """
        def callback(message: Message):
            utterances = message.data.get("utterances", [])
            self.logger.debug(f"[EVENT] User said: {int(round(time.time() * 1000))} - {utterances}")

        self.client.on("recognizer_loop:utterance", callback)

    def listen_for_speak(self):
        """
        Subscribe to messages sent for TTS.
        Message type: "speak"
        """
        def callback(message: Message):
            text = message.data.get("utterance")
            self.logger.debug(f"[EVENT] OVOS will speak: {int(round(time.time() * 1000))} - {text}")

        self.client.on("speak", callback)

    VOICE_CLEAR_DELAY = 5.0
    # ----------------------------------------------------------------------
    # PUBLISH (SEND)
    # ----------------------------------------------------------------------
    def say(self, text):
        """Tell OVOS to speak something."""
        if time.time() - self.last_speak_time > self.VOICE_CLEAR_DELAY:
            msg = Message("speak", {"utterance": text})
            self.client.emit(msg)
            self.last_speak_time = time.time()
            self.logger.debug(f"[SEND] -> {int(round(time.time() * 1000))} - speak: {text}")
        else:
             self.logger.info(f"[SEND - time filter] -> {int(round(time.time() * 1000))} - speak: {text}")

    def getLogger(self, name):
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
