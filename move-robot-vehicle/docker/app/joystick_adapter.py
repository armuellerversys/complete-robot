from concurrent.futures import process
import os
import time
import threading
import glob
from evdev import InputDevice, ecodes
from core_utils import CoreUtils


# Axis normalization configuration
AXIS_MAX = 32767
DEADZONE = 0.15

class JoystickAdapter:
    def __init__(self, vehi_app, devicePath="/dev/input/event5"):
        self.vehi_app = vehi_app
        self.logger = CoreUtils.getLogger(__name__)

        self.thread = None
        self.categorize = None # For event categorization
        self.device_path = devicePath
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
        if abs(norm) < DEADZONE:
            return 0.0
        return norm

    def scale_speed(self, norm_val, max_speed=200):
        """Scales normalized value to motor speed integer (0 to 200)"""
        return int(abs(norm_val) * max_speed)

    def find_gamepad_path(self, device_path):
        """Scans /dev/input/event* inside Docker container to locate gamepads dynamically"""
        # If we already have a device open and its file descriptor is valid, re-use it
        if self.device is not None and self.device.fd != -1 and device_path == self.device.path:
            self.logger.info(f"Using previously connected gamepad: {self.device.path} at {self.device.name}")
            return self.device_path, self.device.name

        # If a specific device_path is provided and exists
        if device_path and os.path.exists(device_path):
            try:
                self.logger.info(f"Attempting to connect to gamepad at specified path: {device_path}")
                self.device = InputDevice(device_path)
                capabilities = self.device.capabilities()
                if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                    self.logger.info(f"Found gamepad at specified path: {device_path} ({self.device.name})")
                    return device_path, self.device.name
                else:
                    self.logger.warning(f"Device at {device_path} is not a valid gamepad. Checking other devices...")
                    self.device.close()
                    self.device = None
            except (PermissionError, FileNotFoundError, OSError):
                self.logger.warning(f"Cannot access {device_path}. Ensure proper permissions or run as root.")
                self.device = None
                return None, None

        # Scan all available event devices
        event_paths = glob.glob('/dev/input/event*')
        for path in event_paths:
            try:
                dev = InputDevice(path)
                capabilities = dev.capabilities()
                if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                    if "keyboard" not in dev.name.lower():
                        self.device = dev
                        self.logger.info(f"Found gamepad at path: {path} ({self.device.name})")
                        return path, self.device.name
                dev.close()
            except (PermissionError, FileNotFoundError, OSError):
                self.logger.warning(f"Cannot access {path}. Ensure proper permissions or run as root.")
                continue

        self.device = None
        return None, None

    def dispatch_movement(self):
        triggerLevel = 0.3
        speed_y = self.scale_speed(self.axis_y)
        speed_x = self.scale_speed(self.axis_x)
        self.logger.debug(f"Receive movement: axis_x={self.axis_x}, axis_y={self.axis_y}, speed_x={speed_x}, speed_y={speed_y}")

        self.instruction = None # Default to stop

        # Center deadzone: Stop motors
        if self.axis_y == 0.0 and self.axis_x == 0.0 and self.last_instruction != 'set_stop':
            self.instruction = {'command': 'set_stop'}
            self.vehi_app.handle_instruction(self.instruction, process=None)
            self.last_instruction = 'set_stop'

        elif self.axis_y != 0.0 or self.axis_x != 0.0:
            self.last_instruction = 'set_joystick'
            self.logger.debug(f"Dispatching movement: axis_x={self.axis_x}, axis_y={self.axis_y}")
            rule = "x"
            if self.axis_y < -triggerLevel:
                if self.axis_x < -triggerLevel or self.axis_x > triggerLevel:
                    rule = "1"
                    self.instruction = {'command': 'set_joystick', 'left_speed': speed_x, 'right_speed': speed_y}
                else:
                    rule = "2"
                    self.instruction = {'command': 'set_joystick', 'left_speed': speed_y, 'right_speed': speed_y}
            
            elif self.axis_y > triggerLevel:
                if self.axis_x < -triggerLevel or self.axis_x > triggerLevel:
                    rule = "3"
                    self.instruction = {'command': 'set_joystick', 'left_speed': -speed_x, 'right_speed': -speed_y}
                else:
                    rule = "4"
                    self.instruction = {'command': 'set_joystick', 'left_speed': -speed_y, 'right_speed': -speed_y}

            if self.axis_y > -triggerLevel and self.axis_y < triggerLevel:
                if self.axis_x < -triggerLevel:
                    rule = "5"
                    self.instruction = {'command': 'set_joystick', 'left_speed': 0, 'right_speed': speed_x}
                    
                if self.axis_x > triggerLevel:
                    rule = "6"
                    self.instruction = {'command': 'set_joystick', 'left_speed': speed_x, 'right_speed': 0}

            if self.instruction is not None:
                if self.instruction.get('left_speed') is not None and self.instruction.get('right_speed') is not None:   
                    self.logger.debug(f"Dispatching instruction: {self.instruction}")
                    if self.axis_x < -triggerLevel or self.axis_x > triggerLevel:
                        self.logger.debug(f"Turning: left_speed={self.instruction['left_speed']}, right_speed={self.instruction['right_speed']}")
                        self.vehi_app.handle_joystick(self.instruction)
                    else:
                        self.logger.debug(f"Moving straight: left_speed={self.instruction['left_speed']}, right_speed={self.instruction['right_speed']}")
                        if self.axis_y < 0:
                            rule = "7"
                            self.vehi_app.run_forward(speed_y)
                        else:
                            rule = "8"
                            self.vehi_app.run_backward(speed_y)

                    self.logger.debug(f"Joystick movement dispatched with rule {rule}: {self.instruction}")
                    self.last_instruction = self.instruction['command']
                    self.instruction = None  # Reset instruction after dispatch
                else:
                    self.logger.debug(f"No valid instruction to dispatch for joystick movement: {self.instruction}")

    def run_event_loop(self, device_path, device_name):
        """Processes events from a connected gamepad"""
        self.logger.info(f"Connected to Gamepad: {device_name} at {device_path}")
        
        try:
            for event in self.device.read_loop():
                if not self.is_running:
                    break

                # Handle Analog Stick Movements
                if event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_Y:
                        self.axis_y = self.normalize_axis(event.value)
                        self.dispatch_movement()
                    elif event.code == ecodes.ABS_X:
                        self.axis_x = self.normalize_axis(event.value)
                        self.dispatch_movement()

                # Handle Buttons
                elif event.type == ecodes.EV_KEY:
                    key_event = self.categorize(event) if self.categorize else None
                    if key_event and key_event.keystate == key_event.key_down:
                        # Emergency Stop button (East / B)
                        if event.code in (ecodes.BTN_EAST, ecodes.BTN_B):
                            self.logger.info("E-Stop triggered via Joystick")
                            self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
                        
                        # Exit script button (Select / Mode)
                        elif event.code in (ecodes.BTN_SELECT, ecodes.BTN_MODE):
                            self.logger.info("Exit instruction sent via Joystick")
                            self.vehi_app.handle_instruction({'command': 'exit'}, process=None)
                            self.is_running = False
        except (OSError, FileNotFoundError):
            self.logger.warning("Joystick disconnected during read loop!")
            self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
        finally:
            self.is_running = False

    def start(self):
        """Main resilience loop that scans and auto-reconnects to gamepads in Docker"""
        self.logger.info(f"Starting Gamepad Controller Service in Docker. Target path: {self.device_path}")
        
        # Safely clean up any existing device reference before loop start
        if self.device is not None:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None

        self.is_running = False   
        while True:
            device_path, device_name = self.connectJoystick()
           
            if self.device is not None and self.device.fd != -1:
                self.logger.info(f"Starting event loop for Gamepad: {self.device}")
                try:
                    self.is_running = True
                    self.thread = threading.Thread(
                        target=self.run_event_loop,
                        name="JoystickVehicleDriver",
                        daemon=True,
                        args=(device_path, device_name)
                    )
                    self.thread.start()
                    self.thread.join()  # Wait for thread execution to complete
                except Exception as e:
                    self.logger.warning(f"Error in joystick thread: {e}")
                    self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
            
            # Reset device state after loop finishes or fails
            if self.device:
                try:
                    self.device.close()
                except Exception:
                    pass
                self.device = None

            self.logger.info("No active gamepad. Retrying in 2 seconds...")
            time.sleep(2)

    def connectJoystick(self):
        device_path, device_name = self.find_gamepad_path(self.device_path)
        if device_name is not None:
            self.logger.info(f"Found Gamepad: {self.device} - {device_name} at {device_path}")
            return device_path, device_name
        else:
            self.logger.warning("No gamepad found. Ensure the joystick is connected and recognized by the system.")
            return None, None

    def stop(self):
        self.is_running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None

        self.vehi_app.handle_joystick({'command': 'set_stop'})
        self.logger.info("JoystickAdapter stopped")