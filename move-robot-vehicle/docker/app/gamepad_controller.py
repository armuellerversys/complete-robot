import os
import time
import logging
import threading
import glob
from evdev import InputDevice, categorize, ecodes

# Import existing vehicle modules
from robot_gpio import Robot
from move_motor import Move_motor
from image_app_core import clear_queue
from vehi_control_example import Vehi_app

# Axis normalization configuration
AXIS_MAX = 32767
DEADZONE = 0.15

def normalize_axis(value):
    """Converts raw analog input (-32768 to 32767) to floating scale (-1.0 to 1.0)"""
    norm = value / AXIS_MAX
    if abs(norm) < DEADZONE:
        return 0.0
    return norm

def scale_speed(norm_val, max_speed=100):
    """Scales normalized value to motor speed integer (0 to 100)"""
    return int(abs(norm_val) * max_speed)

def find_gamepad_path():
    """Scans /dev/input/event* inside Docker container to locate gamepads dynamically"""
    event_paths = glob.glob('/dev/input/event*')
    for path in event_paths:
        try:
            device = InputDevice(path)
            capabilities = device.capabilities()
            # Check if device reports both ABS axes (joysticks) and KEY inputs (buttons)
            if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                # Exclude internal sensors / power buttons
                if "keyboard" not in device.name.lower():
                    return path, device.name
        except (PermissionError, FileNotFoundError, OSError):
            continue
    return None, None

class JoystickVehicleDriver:
    def __init__(self, vehi_app, logger):
        self.vehi_app = vehi_app
        self.logger = logger
        
        # State tracking for steering (X) and throttle (Y)
        self.axis_x = 0.0
        self.axis_y = 0.0
        self.is_running = True

    def dispatch_movement(self):
        """Translates current stick state into Vehi_app commands"""
        speed_y = scale_speed(self.axis_y)
        speed_x = scale_speed(self.axis_x)

        # Center deadzone: Stop motors
        if self.axis_y == 0.0 and self.axis_x == 0.0:
            instruction = {'command': 'set_stop'}
            
        # Forward Movement
        elif self.axis_y < 0:
            if self.axis_x < -0.3:
                instruction = {'command': 'set_forward_left', 'speed': speed_y}
            elif self.axis_x > 0.3:
                instruction = {'command': 'set_forward_right', 'speed': speed_y}
            else:
                instruction = {'command': 'set_forward', 'speed': speed_y, 'distance': 0}

        # Backward Movement
        elif self.axis_y > 0:
            if self.axis_x < -0.3:
                instruction = {'command': 'set_backward_left', 'speed': speed_y}
            elif self.axis_x > 0.3:
                instruction = {'command': 'set_backward_right', 'speed': speed_y}
            else:
                instruction = {'command': 'set_backward', 'speed': speed_y}

        # Spot Turning (Zero Y axis)
        else:
            if self.axis_x < 0:
                instruction = {'command': 'set_left', 'speed': speed_x}
            else:
                instruction = {'command': 'set_right', 'speed': speed_x}

        self.vehi_app.handle_instruction(instruction, process=None)

    def run_event_loop(self, device_path, device_name):
        """Processes events from a connected gamepad"""
        self.logger.info(f"Connected to Gamepad: {device_name} at {device_path}")
        gamepad = InputDevice(device_path)

        for event in gamepad.read_loop():
            if not self.is_running:
                break

            # Handle Analog Stick Movements
            if event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_Y:
                    self.axis_y = normalize_axis(event.value)
                    self.dispatch_movement()
                elif event.code == ecodes.ABS_X:
                    self.axis_x = normalize_axis(event.value)
                    self.dispatch_movement()

            # Handle Buttons
            elif event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                if key_event.keystate == key_event.key_down:
                    # Emergency Stop button (East / B)
                    if event.code in (ecodes.BTN_EAST, ecodes.BTN_B):
                        self.logger.info("E-Stop triggered via Joystick")
                        self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
                    
                    # Exit script button (Select / Mode)
                    elif event.code in (ecodes.BTN_SELECT, ecodes.BTN_MODE):
                        self.logger.info("Exit instruction sent via Joystick")
                        self.vehi_app.handle_instruction({'command': 'exit'}, process=None)
                        self.is_running = False

    def start(self):
        """Main resilience loop that scans and auto-reconnects to gamepads in Docker"""
        self.logger.info("Docker Gamepad Controller Service started. Waiting for Bluetooth joystick...")

        while self.is_running:
            device_path, device_name = find_gamepad_path()

            if device_path:
                try:
                    self.run_event_loop(device_path, device_name)
                except (OSError, FileNotFoundError):
                    self.logger.warning("Joystick disconnected! Halting vehicle and re-scanning...")
                    # Send safety stop command if Bluetooth disconnects abruptly
                    self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
            else:
                # Wait 2 seconds before scanning `/dev/input/` again
                time.sleep(2)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("DockerVehicleLogger")

    # Initialize low-level vehicle drivers
    robot = Robot()
    move_motor = Move_motor()
    
    # Initialize main vehicle application
    vehi_app = Vehi_app(robot, move_motor, logger)

    # Launch driver with auto-reconnect logic
    driver = JoystickVehicleDriver(vehi_app, logger)
    driver.start()