import requests
from ovos_workshop.skills import OVOSSkill
from ovos_workshop.decorators import intent_handler

class VehicleControlSkill(OVOSSkill):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "http://192.168.4.8:5000"
        self.log.info("VehicleControlSkill initialized")

    @intent_handler('vehicle.intent')
    def handle_vehicle_intent(self, message):
        utterance = message.data.get('utterance', '').lower()
        action = "start" if "start" in utterance else "stop"
        
        self.log.info(f"Vehicle command: {action}")
        self.play_beep(message)

        url = f"{self.base_url}/{action}-vehicle"
        try:
            # self.log.info(f"Vehicle {action}: {url}")
            response = self.post_cmd("stop")
            if response.status_code == 200:
                self.speak_dialog(f"vehicle.{action}ed")
            else:
                self.log.error(f"HTTP Error: {response.status_code} for action {action}")
                self.speak("The vehicle controller returned an error.")
        except Exception as e:
            self.log.error(f"HTTP Error: {e}")
            self.speak("I am unable to reach the vehicle controller.")

    @intent_handler('vehicle_status.intent')
    def handle_status_intent(self, message):
        self.log.info("Checking vehicle status...")
        self.play_beep(message)

        try:
            # Assuming your API returns JSON like {"state": "running"}
            response = requests.get(f"{self.base_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                current_status = data.get("state", "unknown")
                # Pass the variable 'status' to the .dialog file
                self.speak_dialog("vehicle_status", data={"status": current_status})
            else:
                self.speak("I couldn't get a valid status from the vehicle.")
        except Exception as e:
            self.log.error(f"Status check failed: {e}")
            self.speak("The vehicle system is not responding to status requests.")

    def play_beep(self, message):
        """Helper to send the beep signal to the audio service"""
        beep_path = "/home/ovos/.local/share/mycroft/sounds/boing_x.wav"
        self.bus.emit(message.forward("mycroft.audio.play_sound", {"uri": f"file://{beep_path}"}))

    def post_cmd(self, action):
     url =  f"http://192.168.4.8:5000/stop"
     self.log.info(f"Post {action}: {url}")
     return requests.post(url)

    ##   $.post('/control', {'command':'set_' + name, 'speed': speed, 'distance': distance });}
    def post_command_json(self, action):
        ## self.base_url
        url = self.base_url + "/control"
        self.log.info(f"Vehicle {action}: {url}")
        # payload = {f"command": set_{action}, speed: 0, distance: 0"}
        payload ={"command": "set_stop", "speed": "80", "distance": "1200"}
        self.log.info(f"Send control request http post-> {url}")
        response = requests.post(self.SERVER_MOVE_URL, data=payload, timeout=4)

def create_skill():
    return VehicleControlSkill()