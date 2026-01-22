import subprocess
from core_utils import CoreUtils

class RobotModes(object):
    """Our robot behaviors and tests as running modes"""

    # Mode config goes from a "mode_name" to a script to run. Configured for look up.
    mode_config = {
        "forward": {"script": "move_behavior.py", "server": True},
        "test_rainbow": {"script": "test_rainbow.py"},
        "test_distance_sensors": {"script": "test_distance_sensors.py"},
        "test_motors": {"script": "test_motors.py"},
        "test_rotate": {"script": "test_full_rotate.py"},
        "test_encoders": {"script": "test_encoders.py"},
        "test_voice_server": {"script": "test_voice_server.py"}
    }

    menu_config = [
        {"mode_name": "forward", "text": "Drive Forward"},
        {"mode_name": "test_rainbow", "text": "LED Rainbow"},
        {"mode_name": "test_distance_sensors", "text": "Test Distance Sensor"},
        {"mode_name": "test_motors", "text": "Test Motors"},
        {"mode_name": "test_rotate", "text": "Test Rotate"},
        {"mode_name": "test_encoders", "text": "Test Encoder"},
        {"mode_name": "test_voice_server", "text": "Test Voice Server"}
    ]

    def __init__(self):
        self.current_process = None
        self.logger = CoreUtils.getLogger("RobotModes")

    def is_running(self):
        """Check if there is a process running. Returncode is only set when a process finishes"""
        return self.current_process and self.current_process.returncode is None

    def run(self, mode_name):
        self.logger.debug(f"RobotModes-Mode name: {mode_name}")
        """Run the mode as a subprocess, but not if we still have one running"""
        while self.is_running():
            self.logger.debug(f"RobotModes-running stop")
            self.stop()

        script = self.mode_config[mode_name]['script']
        self.logger.debug(f"RobotModes-Script: {script}")
        
        self.current_process = subprocess.Popen(["python3", script])
       
        #self.current_process = subprocess.Popen(["python3", "-m", "debugpy", "--listen", "localhost:5678", script])
        # self.current_process = subprocess.Popen(["python3", "-m", "debugpy", "--listen", "localhost:5678", "--wait-for-client", script])
        # self.current_process = subprocess.Popen(["python3",  "-Xfrozen_modules=off", "-m", "debugpy", "--listen", "localhost:5678", "-Xfrozen_modules=off", script])

    def stop(self):
        """RobotModes-Stop a process"""
        self.logger.debug("Try to stop process")
        if self.is_running():
            # Sending the signal sigint is (on Linux) similar to pressing ctrl-c.
            # That causes the behavior to clean up and exit.
            self.current_process.send_signal(subprocess.signal.SIGINT)
            self.logger.debug("Process stopped")
            self.current_process = None

    def should_redirect(self, mode_name):
        return self.mode_config[mode_name].get('server') is True and self.is_running()