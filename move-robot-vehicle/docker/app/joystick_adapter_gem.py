import glob
import os
import select
import threading
import time

from evdev import InputDevice, categorize, ecodes
from core_utils import CoreUtils

AXIS_MAX = 32767
DEADZONE = 0.15
TRIGGER_LEVEL = 0.3


class JoystickAdapter:
    def __init__(self, vehi_app, device_path="/dev/input/event5"):
        self.vehi_app = vehi_app
        self.logger = CoreUtils.getLogger(__name__)

        self.thread = None
        self.service_thread = None

        self.device_path = device_path
        self.device = None

        self.instruction = {'command': 'set_stop'}
        self.last_instruction = 'none'

        self.axis_x = 0.0
        self.axis_y = 0.0

        self.is_running = False
        self._lock = threading.Lock()

        self.logger.info(f"JoystickAdapter initialized on {self.device_path}")

    @staticmethod
    def normalize_axis(value: int) -> float:
        norm = value / AXIS_MAX
        return 0.0 if abs(norm) < DEADZONE else norm

    @staticmethod
    def scale_speed(norm_val: float, max_speed: int = 200) -> int:
        return int(abs(norm_val) * max_speed)

    def connect_joystick(self):
        """Attempts to find and open the input device."""
        if self.device is not None:
            try:
                # Test existing file descriptor
                if self.device.fd != -1 and os.path.exists(self.device.path):
                    return self.device.path, self.device.name
            except Exception:
                self.device = None

        target_path, name = self.find_gamepad_path(self.device_path)
        return target_path, name

    def find_gamepad_path(self, target_path: str):
        if target_path and os.path.exists(target_path):
            try:
                dev = InputDevice(target_path)
                capabilities = dev.capabilities()
                if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                    self.device = dev
                    return target_path, dev.name
                dev.close()
            except (PermissionError, FileNotFoundError, OSError) as err:
                self.logger.warning(f"Cannot access {target_path}: {err}")

        for path in glob.glob('/dev/input/event*'):
            try:
                dev = InputDevice(path)
                capabilities = dev.capabilities()
                if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                    if "keyboard" not in dev.name.lower():
                        self.device = dev
                        return path, dev.name
                dev.close()
            except (PermissionError, FileNotFoundError, OSError):
                continue

        self.device = None
        return None, None

    def start(self):
        """Starts the service thread in the background."""
        with self._lock:
            if self.is_running:
                self.logger.warning("JoystickAdapter service is already running.")
                return

            self.is_running = True
            self.service_thread = threading.Thread(
                target=self._service_loop,
                name="JoystickServiceThread",
                daemon=True
            )
            self.service_thread.start()
            self.logger.info("JoystickAdapter service thread started.")

    def stop(self):
        """Stops event and service threads cleanly without blocking calling worker thread."""
        with self._lock:
            if not self.is_running:
                return
            self.is_running = False

        self.logger.info("Stopping JoystickAdapter...")

        # Unblock event loop I/O immediately
        if self.device:
            try:
                self.device.close()
            except Exception as e:
                self.logger.debug(f"Device close exception during stop: {e}")
            self.device = None

        # Wait briefly for thread completion in background or join non-blockingly
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
            self.thread = None

        if self.service_thread and self.service_thread.is_alive():
            self.service_thread.join(timeout=0.5)
            self.service_thread = None

        self.logger.info("JoystickAdapter successfully stopped.")

    def _service_loop(self):
        self.logger.info(f"Gamepad Service Loop starting on {self.device_path}")

        while self.is_running:
            device_path, device_name = self.connect_joystick()

            if not self.is_running:
                break

            if self.device is not None and self.device.fd != -1:
                self.logger.info(f"Starting event loop for: {device_name}")

                self.thread = threading.Thread(
                    target=self.run_event_loop,
                    name="JoystickVehicleDriver",
                    daemon=True,
                    args=(device_path, device_name)
                )
                self.thread.start()

                # Poll thread state cleanly with short sleep so stop() interrupts immediately
                while self.is_running and self.thread.is_alive():
                    time.sleep(0.1)
            else:
                # Gamepad not connected; wait before retrying to prevent CPU spinning
                time.sleep(1.0)

        self.logger.info("Gamepad Service Loop ended.")

    def run_event_loop(self, device_path: str, device_name: str):
        self.logger.info(f"Event loop active: {device_name}")

        try:
            while self.is_running and self.device is not None:
                try:
                    readable, _, _ = select.select([self.device.fd], [], [], 0.2)
                except (OSError, ValueError):
                    break

                if not self.is_running:
                    break

                if not readable:
                    continue

                try:
                    event = self.device.read_one()
                except (OSError, IOError):
                    self.logger.warning("Joystick disconnected during active read!")
                    break

                if event is None:
                    continue

                # Process events
                if event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_Y:
                        self.axis_y = self.normalize_axis(event.value)
                        self.dispatch_movement()
                    elif event.code == ecodes.ABS_X:
                        self.axis_x = self.normalize_axis(event.value)
                        self.dispatch_movement()

                elif event.type == ecodes.EV_KEY:
                    self.dispatch_button_action(event)

        except Exception as e:
            self.logger.warning(f"Joystick event loop exception: {e}")
        finally:
            self.logger.info("Joystick event loop stopped.")

    def dispatch_movement(self):
        speed_y = self.scale_speed(self.axis_y)
        speed_x = self.scale_speed(self.axis_x)

        if self.axis_y == 0.0 and self.axis_x == 0.0:
            if self.last_instruction != 'set_stop':
                self.instruction = {'command': 'set_stop'}
                self.vehi_app.handle_instruction(self.instruction, process=None)
                self.last_instruction = 'set_stop'
            return

        instruction = {'command': 'set_joystick'}
        is_turning = abs(self.axis_x) > TRIGGER_LEVEL

        if self.axis_y < -TRIGGER_LEVEL:
            instruction.update({'left_speed': speed_x if is_turning else speed_y, 'right_speed': speed_y})
        elif self.axis_y > TRIGGER_LEVEL:
            instruction.update({'left_speed': -speed_x if is_turning else -speed_y, 'right_speed': -speed_y})
        else:
            if self.axis_x < -TRIGGER_LEVEL:
                instruction.update({'left_speed': 0, 'right_speed': speed_x})
            elif self.axis_x > TRIGGER_LEVEL:
                instruction.update({'left_speed': speed_x, 'right_speed': 0})
            else:
                return

        if is_turning:
            self.vehi_app.handle_joystick(instruction)
        else:
            if self.axis_y < 0:
                self.vehi_app.run_forward(speed_y)
            else:
                self.vehi_app.run_backward(speed_y)

        self.last_instruction = 'set_joystick'

    def dispatch_button_action(self, event):
        key_event = categorize(event)
        if key_event.keystate != key_event.key_down:
            return

        if event.code in (ecodes.BTN_NORTH, ecodes.BTN_SOUTH, ecodes.BTN_A, ecodes.BTN_X):
            self.vehi_app.handle_instruction({'command': 'set_stop'}, process=None)
        elif event.code == ecodes.BTN_MODE:
            self.vehi_app.handle_instruction({'command': 'exit'}, process=None)