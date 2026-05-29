from os.path import join, dirname
from ovos_utils.process_utils import RuntimeRequirements
from ovos_workshop.skills import OVOSSkill
from ovos_workshop.decorators import intent_handler
from ovos_bus_client.message import Message

class TestSkill(OVOSSkill):
    def __init__(self, *args, **kwargs):
        self.base_url = "http://example/"
        super().__init__(*args, **kwargs)

    @property
    def runtime_requirements(self):
        # Good practice for OVOS: Specify if internet is needed
        return RuntimeRequirements(
            internet_before_load=False,
            network_before_load=False,
            gui_before_load=False,
            requires_internet=False,
        )

    def initialize(self):
        #import debugpy
        #debugpy.breakpoint()
        self.log.info("TestSkill initialized and ready")    

    @intent_handler('test.intent')
    def handle_test_intent(self, message):
        utterance = message.data.get('utterance', '').lower()
        action = "start" if "start" in utterance else "stop"
        
        self.log.info(f"Test command: {utterance} / {action}")
        self.speak_dialog("test_started.dialog", wait=True)
        self.play_beep(message)

    @intent_handler('test_status.intent')
    def handle_status_intent(self, message):
        self.log.info("Enter Checking test status...")
        self.play_beep(message)

        try:
            # Assuming your API returns JSON like {"state": "running"}
            url = f"{self.base_url}state"
            self.log.info(f"Execute status request to {url}")
            self.speak_dialog("test_status.dialog", wait=True)
            #response = requests.get(url, timeout=5)
            #if response.status_code == 200:
            #   data = response.json()
            # current_status = data.get("state", "unknown")
            # Pass the variable 'status' to the .dialog file
            # self.speak_dialog("test_status", data={"status": current_status})
            #else:
              #  self.log.info(f"Error execute status request with error: {response.status_code}")
              #  self.speak(f"I couldn't get a valid status from the test system")
        except Exception as e:
            self.log.error(f"Status check failed: {e}")
            self.speak("The test system is not responding to status requests.")

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


def create_skill():
    return TestSkill()