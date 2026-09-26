from concurrent.futures import process
import os
import time
import threading
import glob
from evdev import InputDevice, categorize, ecodes
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

        self.last_instruction ='none'
        # State tracking for steering (X) and throttle (Y)
        self.axis_x = 0.0
        self.axis_y = 0.0
        self.is_running = False
        self.logger.info("JoystickAdapter initialized with device path: {}".format(self.device_path))

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
        if self.device is not None:
            return self.device_path, self.device.name
        if device_path and os.path.exists(device_path):
            try:
                self.device = InputDevice(device_path)
                capabilities = self.device.capabilities()
                if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                    self.logger.info(f"Found gamepad at specified path: {device_path} ({self.device.name})")
                    return device_path, self.device.name
            except (PermissionError, FileNotFoundError, OSError):
                self.logger.warning(f"Cannot access {device_path}. Ensure proper permissions or run as root.")
                return None, None
        else:    
            event_paths = glob.glob('/dev/input/event*')
            for path in event_paths:
                try:
                    self.device = InputDevice(path)
                    capabilities = self.device.capabilities()
                    # Check if device reports both ABS axes (joysticks) and KEY inputs (buttons)
                    if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                        # Exclude internal sensors / power buttons
                        if "keyboard" not in self.device.name.lower():
                            return path, self.device.name
                except (PermissionError, FileNotFoundError, OSError):
                    self.logger.warning(f"Cannot access {path}. Ensure proper permissions or run as root.")
                    continue
            return None, None

    def dispatch_movement(self):

        triggerLevel = 0.3
        """Translates current stick state into Vehi_app commands"""

        speed_y = self.scale_speed(self.axis_y)
        speed_x = self.scale_speed(self.axis_x)
        self.logger.debug(f"Dispatching movement: axis_x={self.axis_x}, axis_y={self.axis_y}, speed_x={speed_x}, speed_y={speed_y}")

        self.instruction = None # Default to stop
        # Center deadzone: Stop motors
        if self.axis_y == 0.0 and self.axis_x == 0.0 and self.last_instruction != 'set_stop':
            self.instruction = {'command': 'set_stop'}
            self.vehi_app.handle_instruction(self.instruction, process=None)
            self.last_instruction = 'set_stop'

        elif self.axis_y != 0.0 and self.axis_x != 0.0:
            if self.axis_y < 0:
                self.last_instruction = 'set_joystick'
                self.logger.debug(f"Dispatching y<0 movement: axis_x={self.axis_x}, axis_y={self.axis_y}, speed_x={speed_x}, speed_y={speed_y}")
                if self.axis_x < -triggerLevel:
                    self.instruction = {'command': 'set_joystick', 'left_speed': (speed_y * -1), 'right_speed': (speed_x * -1)}
                elif self.axis_x > triggerLevel:
                    self.instruction = {'command': 'set_joystick', 'left_speed': (speed_y * -1), 'right_speed': speed_x}
            
            elif self.axis_y > 0:
                self.last_instruction = 'set_joystick'
                self.logger.debug(f"Dispatching y>0 movement: axis_x={self.axis_x}, axis_y={self.axis_y}, speed_x={speed_x}, speed_y={speed_y}")
                if self.axis_x < -triggerLevel:
                    self.instruction = {'command': 'set_joystick', 'left_speed': speed_y, 'right_speed': (speed_x * -1)}
                elif self.axis_x > triggerLevel:
                    self.instruction = {'command': 'set_joystick', 'left_speed': speed_y, 'right_speed': speed_x}
            
            if self.instruction is not None:        
                self.logger.debug(f"Dispatching instruction: {self.instruction}")
                self.vehi_app.handle_joystick(self.instruction)
                self.last_instruction = self.instruction['command']
                self.instruction = None  # Reset instruction after dispatch

    def run_event_loop(self, device_path, device_name):
        """Processes events from a connected gamepad"""
        self.logger.info(f"Connected to Gamepad: {device_name} at {device_path}")
       
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
                key_event = self.categorize(event)
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
        self.logger.info(f"Docker Gamepad Controller Service started. Waiting for Bluetooth joystick for event: {self.device_path}")

        while not self.is_running:
            device_path, device_name = self.connectJoystick()
            self.logger.info(f"Found Gamepad: {device_name} at {device_path}")

            if self.device is not None:
                try:
                    self.is_running = True
                    
                    self.thread = threading.Thread(
                        target=self.run_event_loop,
                        name="JoystickVehicleDriver",
                        daemon=True,
                        args=(device_path, device_name)
                    )
            
                    self.thread.start()

                    self.thread.join()  # Wait for the event loop to finish (e.g., on exit)
                except (OSError, FileNotFoundError):
                    self.logger.warning("Joystick disconnected! Halting vehicle and re-scanning...")
                    # Send safety stop command if Bluetooth disconnects abruptly
                    self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
            else:
                # Wait 2 seconds before scanning `/dev/input/` again
                time.sleep(2)

    def connectJoystick(self):
        device_path, device_name = self.find_gamepad_path(self.device_path)
        if device_path is not None:
            self.logger.info(f"Found Gamepad: {device_name} at {device_path}")
        else:
            self.logger.warning("No gamepad found. Ensure the joystick is connected and recognized by the system.")

        return device_path, device_name

    def stop(self):
        self.is_running = False

        if self.thread is not None:
            self.thread.join(timeout=1.0)

        self.vehi_app.handle_joystick({'command': 'set_stop'})

        self.logger.info("JoystickAdapter stopped")

