import subprocess
import signal
import sys
from core_utils import CoreUtils

class RobotModes(object):

    mode_config = {
        "forward": {"script": "move_behavior.py", "server": True},
        "test_rainbow": {"script": "test_rainbow.py"},
        "test_distance_sensors": {"script": "test_distance_sensors.py"},
        "test_motors": {"script": "test_motors.py"},
        "test_encoders": {"script": "test_encoders.py"},
        "test_voice_server": {"script": "test_voice_server.py"}
    }

    menu_config = [
        {"mode_name": "forward", "text": "Drive Forward"},
        {"mode_name": "test_rainbow", "text": "LED Rainbow"},
        {"mode_name": "test_distance_sensors", "text": "Test Distance Sensor"},
        {"mode_name": "test_motors", "text": "Test Motors"},
        {"mode_name": "test_encoders", "text": "Test Encoder"},
        {"mode_name": "test_voice_server", "text": "Test Voice Server"}
    ]

    def __init__(self):
        self.current_process = None
        self.logger = CoreUtils.getLogger("RobotModes")

    def is_running(self):
        return self.current_process and self.current_process.returncode is None

    def run(self, mode_name):
        if mode_name not in self.mode_config:
            raise ValueError(f"Unknown mode: {mode_name}")

        if self.is_running():
            self.stop()

        script = self.mode_config[mode_name]["script"]
        self.logger.info(f"Starting mode: {mode_name} ({script})")

        self.current_process = subprocess.Popen([sys.executable, script])
        self.logger.info(f"PID: {self.current_process.pid}")

    def stop(self):
        if self.is_running():
            self.logger.info("Stopping current process")
            self.current_process.send_signal(signal.SIGINT)
            try:
                self.current_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning("Process did not exit — killing")
                self.current_process.kill()

        self.current_process = None

    def should_redirect(self, mode_name):
        return self.mode_config[mode_name].get('server') is True and self.is_running()
