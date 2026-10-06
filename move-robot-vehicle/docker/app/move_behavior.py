import signal
import sys
import time
import traceback
import debugpy

from core_utils import CoreUtils
from image_app_core import get_control_instruction, start_server_process
from move_app import Move_app
from move_encoder import DriveController
from oled_text import OledText

# Start remote debug listener
try:
    debugpy.listen(("0.0.0.0", 5678))
except Exception:
    pass

HI_TEXT = "Hello Albrecht, my name is K6"
IMAGE_TEXT = "Hello who are you?"
DT = 0.01
TIMEOUT_IN = 100


class MoveBehavior:

    def __init__(self):
        self.logger = CoreUtils.getLogger("MoveBehavior")
        self.logger.info("MoveBehavior: Initializing...")

        self.last_time = time.time()
        self.execute = True
        self.found = False
        self.distance = False
        self.forwardRun = False
        self.server_process = None

        self.move_app = Move_app()
        self.logger.info("MoveBehavior: Move_app created")

        # Indicate initialization status
        self.move_app.set_led_blue()
        self.move_app.stopMotors()

        self.drive_controller = DriveController.getInstance(self)
        self.move_app.setDriveController(self.drive_controller)
        self.oledtext = OledText()
        self.logger.info("MoveBehavior: Initialization complete")

    def process_control(self) -> str:
        instruction = get_control_instruction()
        cmd_type = "_"
        
        while instruction:
            cmd_type = self.move_app.handle_instruction(
                instruction, self.server_process
            )
            self.logger.debug(f"MoveBehavior: Instruction type = {cmd_type}")

            if self.move_app.isCommand(cmd_type):
                self.found = False
                self.last_time = time.time()
                self.move_app.setMatrixString(cmd_type)
                self.execute = True
                if cmd_type == "F":
                    self.forwardRun = True

            if self.move_app.isStop(cmd_type) or self.move_app.isGPad(cmd_type):
                self.forwardRun = False
                self.execute = False


            instruction = get_control_instruction()

        return cmd_type

    def show_text(self, text: str):
        self.logger.info(f"Show text: {text}")
        self.oledtext.show_text(text)

    def process(self):
        self.server_process = start_server_process("move.html")
        # self.logger.info("MoveBehavior: Process started")

        self.move_app.sayText(HI_TEXT)
        self.show_text("HI AL")

        time_pan = time.time()

        while True:
            try:
                cmd_type = self.process_control()
                # self.logger.info("MoveBehavior: command type = " + cmd_type)

                if not cmd_type or cmd_type == "_":
                    self.execute = True
                else:
                    self.execute = False

                self.move_app.set_led_blue()

                if self.forwardRun:
                    self.logger.info("Starting forward drive controller")
                    self.drive_controller.run()
                    self.forwardRun = False

                if self.execute and (time.time() > self.last_time + TIMEOUT_IN):
                    self.move_app.set_led_yellow()
                    self.logger.info("MoveBehavior: Move timeout reached")
                    self.move_app.stopMotors()
                    self.execute = False

                if not self.found and (time.time() > (time_pan + 2)):
                    time_pan = time.time()

                time.sleep(DT)

            except Exception:
                self.logger.error(f"Error in work loop:\n{traceback.format_exc()}")
                self.logger.info("MoveBehavior: Emergency motor stop")
                self.move_app.stopMotors()


def setup_signal_handlers(behavior_instance: MoveBehavior):
    logger = CoreUtils.getLogger("MoveBehavior")

    def handle_exit(sig, frame):
        logger.info(f"Signal {sig} received. Performing emergency cleanup...")

        # 1. Stop motors immediately
        try:
            behavior_instance.move_app.stopMotors()
        except Exception as e:
            logger.error(f"Error stopping motors: {e}")

        # 2. Safely close gpiozero hardware devices
        robot = getattr(behavior_instance.move_app, "robot", None)
        if robot:
            for sensor_name in [
                "left_distance_sensor",
                "right_distance_sensor",
                "mid_distance_sensor",
                "left_encoder",
                "right_encoder",
            ]:
                sensor = getattr(robot, sensor_name, None)
                if sensor and hasattr(sensor, "close"):
                    try:
                        sensor.close()
                    except Exception:
                        pass

        logger.info("GPIO pins released. Safe shutdown complete.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)


if __name__ == "__main__":
    logger = CoreUtils.getLogger("MoveBehavior")
    logger.info("Starting Move Behavior Engine...")

    behavior = MoveBehavior()
    setup_signal_handlers(behavior)

    try:
        behavior.process()
    except Exception as fatal_error:
        logger.error(f"Fatal execution error: {fatal_error}")