from ovos_utils import classproperty
from ovos_utils.log import LOG
from ovos_workshop.intents import IntentBuilder
from ovos_utils.process_utils import RuntimeRequirements
from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills import OVOSSkill
import requests
import time

DEFAULT_SETTINGS = {
    "log_level": "INFO"
}

class MySkillTest(OVOSSkill):

    SERVER_BASE_URL = "http://192.168.4.4:5000/"
    SERVER_MOVE_URL = "http://192.168.4.4:5001/control"
    DT = 2

    def __init__(self, *args, **kwargs):
        """The __init__ method is called when the Skill is first constructed.
        Note that self.bus, self.skill_id, self.settings, and
        other base class settings are only available after the call to super().
        """
        super().__init__(*args, **kwargs)
        # be aware that below is executed after `initialize`
        self.override = True
        
    @classproperty
    def runtime_requirements(self):
        # if this isn't defined the skill will
        # only load if there is internet
        return RuntimeRequirements(
            internet_before_load=False,
            network_before_load=False,
            gui_before_load=False,
            requires_internet=False,
            requires_network=False,
            requires_gui=False,
            no_internet_fallback=True,
            no_network_fallback=True,
            no_gui_fallback=True,
        )
    
    def initialize(self):
        """Performs any final setup of the Skill, for instance to register
        handlers for events that the Skill will respond to.
        This is a good place to load and pre-process any data needed by your Skill.
        """
        # This initializes a settings dictionary that the skill can use to
        # store and retrieve settings. The skill_settings.json file will be
        # created in the location referenced by self.settings_path, which
        # defaults to ~/.config/mycroft/skills/<skill_id>
        # only new keys will be added, existing keys will not be overwritten
        self.settings.merge(DEFAULT_SETTINGS, new_only=True)
        # set a callback to be called when settings are changed
        self.settings_change_callback = self.on_settings_changed
        # (custom) event handler setup example
        # below is a custom event, system event specs found at
        # https://openvoiceos.github.io/message_spec/
        # this can be tested using `mana` (https://github.com/NeonGeckoCom/neon-mana-utils)
        # `mana send-message hello.world`
        self.add_event("hello.robot", self.handle_hello_robot_intent)
        self.my_var = "hello robot"

    def on_settings_changed(self):
        """This method is called when the skill settings are changed."""
        LOG.info("Settings changed!")

    @property
    def log_level(self):
        """Dynamically get the 'log_level' value from the skill settings file.
        If it doesn't exist, return the default value.
        This will reflect live changes to settings.json files (local or from backend)
        """
        return self.settings.get("log_level", "INFO")
    
    def handle_hello_robot_intent(self, message):
        """
        Handler for the custom 'hello.robot' event.
        This method was missing, causing the AttributeError.
        """
        LOG.info(f"Received hello.robot event with message: {message.data}")
        self.speak_dialog("hello.robot.response", data={"my_var": self.my_var})
        # You can add more logic here based on what you want this event to do.

    @intent_handler(IntentBuilder("TestRainbow")
                    .require("Robot")
                    .require("TestRainbow"))
    def handle_test_rainbow(self, message):
        try:
            LOG.info("Enter handle_test_rainbow")
            self.speak_dialog("try Testing Rainbow")
            self.handle_control('run/test_rainbow', 'Test Rainbow done')
        except:
            self.speak_dialog("UnableToIntend")
            LOG.exception("Unable to reach intend TestRainbow")

    @intent_handler(IntentBuilder("Stop")
                    .require("Robot")
                    .require("stop"))
    def handle_stop(self, message):
        try:
            LOG.info("Enter handle_stop")
            self.speak_dialog("try Stop Robot")
            self.handle_control('stop', 'Stop Robot done')
        except:
            self.speak_dialog("UnableToIntend")
            LOG.exception("Unable to reach intend Stop")

    @intent_handler(IntentBuilder("Forward")
                    .require("Robot")
                    .require("forward"))
    def handle_forward(self, message):
        try:
            LOG.info("Enter handle_forward")
            self.speak_dialog("try forward robot")
            self.handle_move_control('set_forward', 'forward robot done')
        except:
            self.speak_dialog("UnableToIntend")
            LOG.exception("Unable to reach intend Forward")

    @intent_handler(IntentBuilder("Backward")
                    .require("Robot")
                    .require("backward"))
    def handle_backward(self, message):
        try:
            LOG.info("Enter handle_backward")
            self.speak_dialog("try backward robot")
            self.handle_move_control('set_backward', 'backward robot done')
        except:
            self.speak_dialog("UnableToIntend")
            LOG.exception("Unable to reach intend Backward")

    @intent_handler(IntentBuilder("Turnright")
                    .require("Robot")
                    .require("turnright"))
    def handle_turnright(self, message):
        try:
            LOG.info("Enter handle_turnright")
            self.speak_dialog("try turn right robot")
            self.handle_move_control('set_turnright', 'turn right robot done')
        except:
            self.speak_dialog("UnableToIntend")
            LOG.exception("Unable to reach intend Turnright")

    @intent_handler(IntentBuilder("Turnleft")
                    .require("Robot")
                    .require("turnleft"))
    def handle_turnleft(self, message):
        try:
            LOG.info("Enter handle_turnleft")
            self.speak_dialog("try turn left robot")
            self.handle_move_control('set_turnleft', 'turn left robot done')
        except:
            self.speak_dialog("UnableToIntend")
            LOG.exception("Unable to reach intend Turnleft")

    def handle_move_control(self, end_point, dialog_verb):
        try:
            url = self.SERVER_BASE_URL + "run/forward"
            LOG.info(f"Handle_move_control: {url}!")
            requests.post(url)
            self.speak_dialog("Forward run send")
           
            time.sleep(10)

            #payload ={"command": end_point,"speed": "80","distance": "1200"}
            payload ={"command": "set_forward", "speed": "80", "distance": "1200"}
            LOG.info(f"Send control request http post-> {self.SERVER_MOVE_URL}")
            response = requests.post(self.SERVER_MOVE_URL, data=payload, timeout=4)
            LOG.info(f"Receive control request http return-> {response.status_code}")
            self.speak_dialog(dialog_verb)
        except:
            self.speak_dialog("UnableToReach")
            LOG.exception("Unable to reach the robot")

    def handle_control(self, end_point, dialog_verb):
        try:
            url = self.SERVER_BASE_URL + end_point
            LOG.info(f"Handle_control: {url}!")
            requests.post(url)
            self.speak_dialog(dialog_verb)
        except:
            self.speak_dialog("UnableToReach")
            LOG.exception("Unable to reach the robot")
