from ovos_bus_client.client import MessageBusClient
import time
import sys
from ovos_bus_client.message import Message
import os
import logging


class SoundServer():

    def __init__(self):
        self.logger = self.getLogger()
        self.bus = MessageBusClient()

    def play_sound(self):
            # Check if the sound file exists
            sound_path = "/home/ovos/.config/mycroft/boing_x.wav"
            if not os.path.isfile(sound_path):
                self.log.error(f"Sound file not found: {sound_path}")
                return
    
            #"""Helper to send the beep signal to the audio service"""

    def play_beep(self, message):
        self.log.info("Enter play_beep...")
        if not self.bus:
            self.log.warning("Bus not ready, skipping beep")
            return

        #"""Helper to send the beep signal to the audio service"""
        sound_path = "/home/ovos/.config/mycroft/boing_x.wav"

        # 1. Get the absolute path to your WAV file inside the skill's folder
        # Assumes your file is located at: your_skill_folder/res/snd/alert.wav
        ## sound_path = join(dirname(__file__), "res", "snd", "boing_x.wav")

        self.log.info(f"Sound path: {sound_path}")

        # 2. Construct the MessageBus payload
        # The audio subsystem expects 'uri' containing the file path
        message_data = {"uri": f"file://{sound_path}"}

        # 3. Emit the message to the OVOS MessageBus
        self.bus.emit(Message("mycroft.audio.play-sound", data=message_data))

        self.play_audio(f"file://{sound_path}")

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