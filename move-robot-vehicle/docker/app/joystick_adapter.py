import os
import time
import threading
import glob
from evdev import InputDevice, ecodes
from core_utils import CoreUtils


# Axis normalization configuration
AXIS_MAX = 32767
DEADZONE = 0.15
TRIGGER_LEVEL = 0.3

class JoystickAdapter:
    def __init__(self, vehi_app, device_path="/dev/input/event5"):
        self.vehi_app = vehi_app
        self.logger = CoreUtils.getLogger(__name__)

        self.thread = None
        self.device_path = device_path
        self.device = None

        self.instruction = {'command': 'set_stop'}
        self.last_instruction = 'none'
        
        # State tracking for steering (X) and throttle (Y)
        self.axis_x = 0.0
        self.axis_y = 0.0
        self.is_running = False
        self.logger.info(f"JoystickAdapter initialized with device path: {self.device_path}")

    def normalize_axis(self, value):
        """Converts raw analog input (-32768 to 32767) to floating scale (-1.0 to 1.0)"""
        norm = value / AXIS_MAX
        return 0.0 if abs(norm) < DEADZONE else norm

    def scale_speed(self, norm_val, max_speed=200):
        """Scales normalized value to motor speed integer (0 to 200)"""
        return int(abs(norm_val) * max_speed)

    def find_gamepad_path(self, target_path):
        """Scans /dev/input/event* to locate gamepads dynamically"""
        # Re-use current device if already open and matching
        if self.device and self.device.fd != -1 and target_path == self.device.path:
            self.logger.info(f"Using previously connected gamepad: {self.device.path} ({self.device.name})")
            return self.device.path, self.device.name

        # Check target path first
        paths_to_check = [target_path] if target_path and os.path.exists(target_path) else []
        paths_to_check.extend(glob.glob('/dev/input/event*'))

        for path in paths_to_check:
            try:
                dev = InputDevice(path)
                capabilities = dev.capabilities()
                is_gamepad = ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities
                
                if is_gamepad and "keyboard" not in dev.name.lower():
                    self.device = dev
                    self.logger.info(f"Found gamepad at path: {path} ({self.device.name})")
                    return path, self.device.name
                dev.close()
            except (PermissionError, FileNotFoundError, OSError):
                continue

        self.device = None
        return None, None

    def dispatch_movement(self):
        speed_y = self.scale_speed(self.axis_y)
        speed_x = self.scale_speed(self.axis_x)

        # 1. Neutral / Deadzone Stop
        if self.axis_y == 0.0 and self.axis_x == 0.0:
            if self.last_instruction != 'set_stop':
                self.instruction = {'command': 'set_stop'}
                self.vehi_app.handle_instruction(self.instruction, process=None)
                self.last_instruction = 'set_stop'
            return

        # 2. Movement Logic
        self.last_instruction = 'set_joystick'
        is_turning = abs(self.axis_x) > TRIGGER_LEVEL
        is_moving_y = abs(self.axis_y) > TRIGGER_LEVEL

        if is_turning:
            # Turning maneuvers
            if self.axis_y < -TRIGGER_LEVEL:
                left, right = speed_x, speed_y
            elif self.axis_y > TRIGGER_LEVEL:
                left, right = -speed_x, -speed_y
            else:
                # Pivot on the spot
                left = 0 if self.axis_x < 0 else speed_x
                right = speed_x if self.axis_x < 0 else 0

            self.instruction = {'command': 'set_joystick', 'left_speed': left, 'right_speed': right}
            self.vehi_app.handle_joystick(self.instruction)

        elif is_moving_y:
            # Straight Forward / Backward
            if self.axis_y < 0:
                self.vehi_app.run_forward(speed_y)
            else:
                self.vehi_app.run_backward(speed_y)

    def run_event_loop(self, device_path, device_name):
        """Processes input events from the connected gamepad"""
        self.logger.info(f"Connected to Gamepad: {device_name} at {device_path}")
        
        try:
            for event in self.device.read_loop():
                if not self.is_running:
                    break

                # Handle Axis Movement
                if event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_Y:
                        self.axis_y = self.normalize_axis(event.value)
                        self.dispatch_movement()
                    elif event.code == ecodes.ABS_X:
                        self.axis_x = self.normalize_axis(event.value)
                        self.dispatch_movement()

                # Handle Button Press (key_down)
                elif event.type == ecodes.EV_KEY and event.value == 1:
                    # Emergency Stop (B / East)
                    if event.code in (ecodes.BTN_EAST, ecodes.BTN_B):
                        self.logger.info("E-Stop triggered via Joystick")
                        self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
                    
                    # Exit (Select / Mode)
                    elif event.code in (ecodes.BTN_SELECT, ecodes.BTN_MODE):
                        self.logger.info("Exit instruction sent via Joystick")
                        self.vehi_app.handle_instruction({'command': 'exit'}, process=None)
                        self.is_running = False

        except (OSError, FileNotFoundError):
            self.logger.warning("Joystick disconnected during read loop!")
            self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
        finally:
            self.is_running = False

    def connect_joystick(self):
        """Helper to discover and locate connected joystick"""
        device_path, device_name = self.find_gamepad_path(self.device_path)
        if device_name:
            self.logger.info(f"Found Gamepad: {device_name} at {device_path}")
            return device_path, device_name
        self.logger.warning("No gamepad found. Ensure joystick is connected.")
        return None, None

    def start(self):
        """Main connection loop with auto-reconnect capability"""
        self.logger.info(f"Starting Gamepad Controller Service. Target path: {self.device_path}")
        self.is_running = True

        while self.is_running:
            device_path, device_name = self.connect_joystick()
           
            if self.device and self.device.fd != -1:
                try:
                    self.run_event_loop(device_path, device_name)
                except Exception as e:
                    self.logger.warning(f"Error in joystick loop: {e}")
                    self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
            
            # Safe cleanup before retry
            if self.device:
                try:
                    self.device.close()
                except Exception:
                    pass
                self.device = None

            if self.is_running:
                self.logger.info("No active gamepad. Retrying in 2 seconds...")
                time.sleep(2)

    def stop(self):
        self.is_running = False
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None

        self.vehi_app.handle_joystick({'command': 'set_stop'})
        self.logger.info("JoystickAdapter stopped")