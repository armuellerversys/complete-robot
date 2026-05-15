from ovos_workshop.skills import OVOSSkill
from ovos_workshop.decorators import intent_handler

class TestSkill(OVOSSkill):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):
        self.log.info("TestSkill initialized and ready")    

    @intent_handler('test.intent')
    def handle_test_intent(self, message):
        utterance = message.data.get('utterance', '').lower()
        action = "start" if "start" in utterance else "stop"
        
        self.log.info(f"Test command: {utterance} / {action}")
        self.play_beep(message)

    @intent_handler('test_status.intent')
    def handle_status_intent(self, message):
        self.log.info("Enter Checking test status...")
        self.play_beep(message)

        try:
            # Assuming your API returns JSON like {"state": "running"}
            url = f"{self.base_url}state"
            self.log.info(f"Execute status request to {url}")
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
        
        if not self.bus:
            self.log.warning("Bus not ready, skipping beep")
            return

        """Helper to send the beep signal to the audio service"""
        beep_path = "/home/ovos/.local/share/mycroft/sounds/boing_x.wav"
        self.bus.emit(message.forward(
            "mycroft.audio.play_sound", {"uri": f"file://{beep_path}"}))


def create_skill():
    return TestSkill()