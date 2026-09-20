import time
import logging
import threading
from evdev import InputDevice, categorize, ecodes

# Import existing modules
from robot_gpio import Robot
from move_motor import Move_motor
from image_app_core import clear_queue
from vehi_control_example import Vehi_app  # Assuming your file is named vehi_control_example.py

# Path to your paired gamepad (check using: python3 -m evdev.evtest)
# GAMEPAD_PATH = '/dev/input/event5'
GAMEPAD_PATH = '/dev/input/event5'

# Axis configuration for typical Bluetooth gamepads
# Hardware max range is usually 32767 for analog sticks
AXIS_MAX = 32767
DEADZONE = 0.15  # 15% deadzone to prevent drift when stick is centered


def __init__(self):
    # Setup logger required by Vehi_app
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("VehicleLogger")

    # Start joystick listener driver
    driver = JoystickVehicleDriver(vehi_app, GAMEPAD_PATH)
    driver.run()

def normalize_axis(value):
    """Converts raw analog input (-32768 to 32767) to a floating scale (-1.0 to 1.0)"""
    norm = value / AXIS_MAX
    if abs(norm) < DEADZONE:
        return 0.0
    return norm

def scale_speed(norm_val, max_speed=100):
    """Scales normalized value (-1.0 to 1.0) to motor speed integer (0 to 100)"""
    return int(abs(norm_val) * max_speed)

class JoystickVehicleDriver:
    def __init__(self, vehi_app, gamepad_path):
        self.vehi_app = vehi_app
        self.gamepad_path = gamepad_path
        
        # State tracking for steering (X) and throttle (Y)
        self.axis_x = 0.0  # -1.0 (left) to 1.0 (right)
        self.axis_y = 0.0  # -1.0 (forward) to 1.0 (backward)
        
        self.is_running = True

    def dispatch_movement(self):
        """Translates current stick position into Vehi_app instructions"""
        speed_y = scale_speed(self.axis_y)
        speed_x = scale_speed(self.axis_x)

        # Center deadzone: Stop motors
        if self.axis_y == 0.0 and self.axis_x == 0.0:
            instruction = {'command': 'set_stop'}
            
        # Forward Movements
        elif self.axis_y < 0:  # Joystick pushed UP/Forward
            if self.axis_x < -0.3:
                instruction = {'command': 'set_forward_left', 'speed': speed_y}
            elif self.axis_x > 0.3:
                instruction = {'command': 'set_forward_right', 'speed': speed_y}
            else:
                # Default distance set to 0 for continuous live manual control
                instruction = {'command': 'set_forward', 'speed': speed_y, 'distance': 0}

        # Backward Movements
        elif self.axis_y > 0:  # Joystick pulled DOWN/Backward
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

        # Send instruction to existing vehicle logic (process parameter set to None)
        self.vehi_app.handle_instruction(instruction, process=None)

    def run(self):
        """Main loop listening to evdev input events"""
        try:
            gamepad = InputDevice(self.gamepad_path)
            print(f"Connected to Bluetooth Joystick: {gamepad.name}")

            for event in gamepad.read_loop():
                if not self.is_running:
                    break

                # Handle Analog Stick Movement (ABS events)
                if event.type == ecodes.EV_ABS:
                    # ABS_Y: Vertical Left Stick (Forward/Backward)
                    if event.code == ecodes.ABS_Y:
                        self.axis_y = normalize_axis(event.value)
                        self.dispatch_movement()

                    # ABS_X: Horizontal Left Stick (Steering)
                    elif event.code == ecodes.ABS_X:
                        self.axis_x = normalize_axis(event.value)
                        self.dispatch_movement()

                # Handle Button Events (KEY events)
                elif event.type == ecodes.EV_KEY:
                    key_event = categorize(event)
                    if key_event.keystate == key_event.key_down:
                        # BTN_EAST / BTN_B for emergency stop
                        if event.code == ecodes.BTN_EAST or event.code == ecodes.BTN_B:
                            print("E-Stop triggered via Joystick")
                            self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
                            
                        # BTN_SELECT / BTN_MODE to safely exit system
                        elif event.code == ecodes.BTN_SELECT:
                            print("Exiting application...")
                            self.vehi_app.handle_instruction({'command': 'exit'}, process=None)
                            self.is_running = False

        except FileNotFoundError:
            print(f"Device not found at {self.gamepad_path}. Check Bluetooth connection.")
        except PermissionError:
            print("Permission denied accessing /dev/input/. Run with sudo or add user to 'input' group.")
