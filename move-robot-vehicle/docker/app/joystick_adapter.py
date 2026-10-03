import glob
import os
import threading
import time
from evdev import InputDevice, categorize, ecodes
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
        self.logger.info(f"JoystickAdapter initialized with default path: {self.device_path}")

    @staticmethod
    def normalize_axis(value: int) -> float:
        """Converts raw analog input (-32768 to 32767) to normalized float scale (-1.0 to 1.0)."""
        norm = value / AXIS_MAX
        if abs(norm) < DEADZONE:
            return 0.0
        return norm

    @staticmethod
    def scale_speed(norm_val: float, max_speed: int = 200) -> int:
        """Scales normalized float (-1.0 to 1.0) to motor speed integer (0 to max_speed)."""
        return int(abs(norm_val) * max_speed)

    def find_gamepad_path(self, target_path: str):
        """Scans /dev/input/event* inside Docker container to locate gamepads dynamically."""
        # Reuse current active connection if still valid
        if self.device is not None and self.device.fd != -1 and target_path == self.device.path:
            self.logger.info(f"Using previously connected gamepad: {self.device.path} ({self.device.name})")
            return self.device.path, self.device.name

        # Check explicitly provided target_path
        if target_path and os.path.exists(target_path):
            try:
                self.logger.info(f"Attempting connection to specified path: {target_path}")
                dev = InputDevice(target_path)
                capabilities = dev.capabilities()
                if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                    self.device = dev
                    self.logger.info(f"Found gamepad at path: {target_path} ({dev.name})")
                    return target_path, dev.name
                dev.close()
            except (PermissionError, FileNotFoundError, OSError) as err:
                self.logger.warning(f"Cannot access {target_path}: {err}")

        # Fall back to scanning all event nodes
        for path in glob.glob('/dev/input/event*'):
            try:
                dev = InputDevice(path)
                capabilities = dev.capabilities()
                if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                    if "keyboard" not in dev.name.lower():
                        self.device = dev
                        self.logger.info(f"Dynamically discovered gamepad at: {path} ({dev.name})")
                        return path, dev.name
                dev.close()
            except (PermissionError, FileNotFoundError, OSError):
                continue

        self.device = None
        return None, None

    def dispatch_movement(self):
        """Evaluates current X/Y axes and sends movement instructions to vehicle."""
        speed_y = self.scale_speed(self.axis_y)
        speed_x = self.scale_speed(self.axis_x)

        # Center deadzone state: issue stop once when transitioning to rest
        if self.axis_y == 0.0 and self.axis_x == 0.0:
            if self.last_instruction != 'set_stop':
                self.instruction = {'command': 'set_stop'}
                self.vehi_app.handle_instruction(self.instruction, process=None)
                self.last_instruction = 'set_stop'
            return

        instruction = {'command': 'set_joystick'}
        is_turning = abs(self.axis_x) > TRIGGER_LEVEL

        # Handle Forward / Reverse / Turning Logic
        if self.axis_y < -TRIGGER_LEVEL:
            if is_turning:
                instruction.update({'left_speed': speed_x, 'right_speed': speed_y})
            else:
                instruction.update({'left_speed': speed_y, 'right_speed': speed_y})

        elif self.axis_y > TRIGGER_LEVEL:
            if is_turning:
                instruction.update({'left_speed': -speed_x, 'right_speed': -speed_y})
            else:
                instruction.update({'left_speed': -speed_y, 'right_speed': -speed_y})

        else:  # Y is within central neutral band
            if self.axis_x < -TRIGGER_LEVEL:  # Turn Left on spot
                instruction.update({'left_speed': 0, 'right_speed': speed_x})
            elif self.axis_x > TRIGGER_LEVEL:  # Turn Right on spot
                instruction.update({'left_speed': speed_x, 'right_speed': 0})
            else:
                return  # No significant axis deflection

        # Execute instruction
        self.logger.debug(f"Dispatching movement: {instruction}")
        if is_turning:
            self.vehi_app.handle_joystick(instruction)
        else:
            if self.axis_y < 0:
                self.vehi_app.run_forward(speed_y)
            else:
                self.vehi_app.run_backward(speed_y)

        self.last_instruction = 'set_joystick'

    def dispatch_button_action(self, event):
        """Handles button press events and maps them to vehicle commands."""
        key_event = categorize(event)
        self.logger.info(f"Button event: {key_event.keycode} - State: {key_event.keystate}")

        if key_event.keystate == key_event.key_down:
            instruction = {'command': 'set_joystick'}
            if event.code in (ecodes.BTN_NORTH, ecodes.BTN_X):
                self.logger.info("BTN_NORTH triggered via GPAD button")
                self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
            elif event.code in (ecodes.BTN_SOUTH, ecodes.BTN_A):
                self.logger.info("BTN_SOUTH triggered via GPAD button")
                self.vehi_app.handle_instruction({'command': 'exit'}, process=None)
            elif event.code in (ecodes.BTN_EAST, ecodes.BTN_B):
                self.logger.info("BTN_EAST triggered via GPAD button 305")
                instruction.update({'left_speed': 150, 'right_speed': -150})
                self.vehi_app.handle_joystick(instruction)
            elif event.code in (ecodes.BTN_WEST, ecodes.BTN_Y):
                self.logger.info("BTN_WEST triggered via GPAD button")
                instruction.update({'left_speed': -150, 'right_speed': 150})
                self.vehi_app.handle_joystick(instruction)
            elif event.code == (ecodes.BTN_Z):
                self.logger.info("BTN_Z triggered via GPAD button")
                self.vehi_app.handle_instruction({'command': 'exit'}, process=None)
            elif event.code == (ecodes.BTN_MODE):
                self.logger.info("BTN_MODE triggered via GPAD button")
                self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
            elif event.code == (ecodes.BTN_SELECT):
                self.logger.info("BTN_SELECT triggered via GPAD button")
            else:
                self.logger.info("BTN_SELECT Exit instruction sent via Joystick")
                
        return None

    def run_event_loop(self, device_path: str, device_name: str):
        """Processes incoming events from the connected gamepad."""
        self.logger.info(f"Connected event loop started: {device_name} ({device_path})")

        try:
            for event in self.device.read_loop():
                if not self.is_running:
                    break

                self.logger.info(f"Event Type: {event.type}, Code: {event.code}, Value: {event.value}")
                instruction = {'command': 'set_joystick'}
                # Analog stick movements
                if event.type == ecodes.EV_ABS: # Analog stick movements value 3
                    if event.code == ecodes.ABS_Y:
                        self.axis_y = self.normalize_axis(event.value)
                        self.dispatch_movement()
                    elif event.code == ecodes.ABS_X:
                        self.axis_x = self.normalize_axis(event.value)
                        self.dispatch_movement()
                    if event.code == ecodes.ABS_RX:
                        self.axis_y = self.normalize_axis(event.value)
                        self.logger.info(f"ABS_RX Analog stick value: {event.value}")
                    elif event.code == ecodes.ABS_RY:
                        self.axis_x = self.normalize_axis(event.value)
                        self.logger.info(f"ABS_RY Analog stick value: {event.value}")
                    elif event.code == ecodes.ABS_HAT0X:  # Left Trigger
                        self.logger.info(f"ABS_HAT0X Trigger  value: {event.value}")
                        if event.value <= 0:  # Up
                            instruction.update({'left_speed': 150, 'right_speed': -150})
                        else:
                            instruction.update({'left_speed': -150, 'right_speed': 150})
                        self.vehi_app.handle_joystick(instruction)
                    elif event.code == ecodes.ABS_HAT0Y:  # Right Trigger
                        self.logger.info(f"ABS_HAT0Y Trigger value: {event.value}")
                        if event.value <= 0:  # Up
                            instruction.update({'left_speed': 150, 'right_speed': 150})
                        else:
                            instruction.update({'left_speed': -150, 'right_speed': -150})
                        self.vehi_app.handle_joystick(instruction)
                    elif event.code == ecodes.BTN_TL:  # 310
                        self.logger.info(f"BTN_TL Button value: {event.value}")
                        instruction.update({'left_speed': 150, 'right_speed': -150})
                        self.vehi_app.handle_joystick(instruction)
                    elif event.code == ecodes.BTN_TR:  # 311
                        self.logger.info(f"BTN_TR Button value: {event.value}")
                        instruction.update({'left_speed': -150, 'right_speed': 150})
                        self.vehi_app.handle_joystick(instruction)
                    else:
                        self.logger.debug(f"Unhandled ABS event {event}: Code {event.code}, Value {event.value}")

                # Button events
                elif event.type == ecodes.EV_KEY: # Button events value 1
                    self.dispatch_button_action(event)
                    
        except (OSError, FileNotFoundError):
            self.logger.warning("Joystick disconnected during active read loop!")
            self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
        finally:
            self.is_running = False

    def start(self):
        """Main resilience loop that scans and auto-reconnects to gamepads."""
        self.logger.info(f"Starting Gamepad Service. Target path: {self.device_path}")
        self.is_running = True

        if self.device is not None:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None

        while self.is_running:
            device_path, device_name = self.connect_joystick()

            if self.device is not None and self.device.fd != -1:
                self.logger.info(f"Starting event loop thread for Gamepad: {self.device.name}")
                try:
                    self.thread = threading.Thread(
                        target=self.run_event_loop,
                        name="JoystickVehicleDriver",
                        daemon=True,
                        args=(device_path, device_name)
                    )
                    self.thread.start()
                    self.thread.join()  # Wait until thread exits (e.g. disconnect or exit button)
                except Exception as e:
                    self.logger.warning(f"Error in joystick thread: {e}")
                    self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)

            # Cleanup closed device instance before retry
            if self.device:
                try:
                    self.device.close()
                except Exception:
                    pass
                self.device = None

            if self.is_running:
                self.logger.info("No active gamepad. Retrying connection in 2 seconds...")
                time.sleep(2)

    def connect_joystick(self):
        """Attempts to discover and lock onto an available joystick."""
        device_path, device_name = self.find_gamepad_path(self.device_path)
        if device_name is not None:
            self.logger.info(f"Successfully locked onto Gamepad: {device_name} at {device_path}")
            return device_path, device_name

        self.logger.warning("No gamepad found. Waiting for device connection...")
        return None, None

    def stop(self):
        """Stops the event loop and safely closes device connections."""
        self.is_running = False
        if self.device:
            try:
                self.device.close()
                if self.thread and self.thread.is_alive():
                    self.thread.join(timeout=1.0)
            except Exception:
                pass
            self.device = None

        self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
        self.logger.info("JoystickAdapter successfully stopped.")