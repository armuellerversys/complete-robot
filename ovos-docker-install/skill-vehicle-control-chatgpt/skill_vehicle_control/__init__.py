import requests
from ovos_workshop.skills import OVOSSkill
from ovos_workshop.decorators import intent_handler
from ovos_utils.process_utils import RuntimeRequirements
from ovos_utils.gui import GUIInterface

class VehicleControlSkill(OVOSSkill):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "http://192.168.4.6:5000" 

    @intent_handler('vehicle.intent')
    def handle_vehicle_intent(self, message):
        # Determine action from the utterance
        utterance = message.data.get('utterance', '').lower()
        action = "start" if "start" in utterance else "stop"
        
        self.log.info(f"Vehicle command: {action}")

        # 1. Play the beep
        # In modern OVOS, we can send a message to the audio service
        beep_path = "/home/ovos/.local/share/mycroft/sounds/boing_x.wav"
        self.bus.emit(message.forward("mycroft.audio.play_sound", {"uri": f"file://{beep_path}"}))

        # 2. HTTP POST Request
        url = f"{self.base_url}/{action}-vehicle"
        try:
            response = requests.post(url, timeout=5)
            if response.status_code == 200:
                # Trigger the dialog files you created
                self.speak_dialog(f"vehicle.{action}ed")
            else:
                self.speak("The vehicle controller returned an error.")
        except Exception as e:
            self.log.error(f"HTTP Error: {e}")
            self.speak("I am unable to reach the vehicle controller.")

def create_skill():
    return VehicleControlSkill()