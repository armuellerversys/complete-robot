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
    """
    Non-blocking Gamepad Service utilizing evdev and thread-safe dispatching.
    """

    def __init__(self, vehi_app, device_path="/dev/input/event5"):
        self.vehi_app = vehi_app
        self.logger = CoreUtils.getLogger(__name__)

        self.device_path = device_path
        self.device = None

        self.thread = None
        self.service_thread = None

        self.instruction = {"command": "set_stop"}
        self.last_instruction = "none"

        self.axis_x = 0.0
        self.axis_y = 0.0

        self.is_running = False
        self._stop_event = threading.Event()

        self.logger.info(f"JoystickAdapter configured for target path: {self.device_path}")

    @staticmethod
    def normalize_axis(value: int) -> float:
        norm = value / AXIS_MAX
        if abs(norm) < DEADZONE:
            return 0.0
        return norm

    @staticmethod
    def scale_speed(norm_val: float, max_speed: int = 200) -> int:
        return int(abs(norm_val) * max_speed)

    def find_gamepad_path(self, target_path: str):
        if self.device is not None and self.device.fd != -1 and target_path == self.device.path:
            return self.device.path, self.device.name

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

        for path in glob.glob("/dev/input/event*"):
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

    def dispatch_movement(self):
        speed_y = self.scale_speed(self.axis_y)
        speed_x = self.scale_speed(self.axis_x)

        if self.axis_y == 0.0 and self.axis_x == 0.0:
            if self.last_instruction != "set_stop":
                self.instruction = {"command": "set_stop"}
                self.vehi_app.handle_instruction(self.instruction, process=None)
                self.last_instruction = "set_stop"
            return

        instruction = {"command": "set_joystick"}
        is_turning = abs(self.axis_x) > TRIGGER_LEVEL

        if self.axis_y < -TRIGGER_LEVEL:
            if is_turning:
                instruction.update({"left_speed": speed_x, "right_speed": speed_y})
            else:
                instruction.update({"left_speed": speed_y, "right_speed": speed_y})
        elif self.axis_y > TRIGGER_LEVEL:
            if is_turning:
                instruction.update({"left_speed": -speed_x, "right_speed": -speed_y})
            else:
                instruction.update({"left_speed": -speed_y, "right_speed": -speed_y})
        else:
            if self.axis_x < -TRIGGER_LEVEL:
                instruction.update({"left_speed": 0, "right_speed": speed_x})
            elif self.axis_x > TRIGGER_LEVEL:
                instruction.update({"left_speed": speed_x, "right_speed": 0})
            else:
                return

        if is_turning:
            self.vehi_app.handle_joystick(instruction)
        else:
            if self.axis_y < 0:
                self.vehi_app.run_forward(speed_y)
            else:
                self.vehi_app.run_backward(speed_y)

        self.last_instruction = "set_joystick"

    def dispatch_button_action(self, event):
        key_event = categorize(event)
        if key_event.keystate != key_event.key_down:
            return None

        self.logger.info(
            f"Button event: {key_event.keycode} - "
            f"State: {key_event.keystate}"
        )

        instruction = {"command": "set_joystick"}

        if event.code in (ecodes.BTN_SELECT, ecodes.BTN_Z): #309
            self.vehi_app.handle_instruction({"command": "set_stop"}, process=None)

        if event.code in (ecodes.BTN_NORTH, ecodes.BTN_X):  # 307 - drive managed
            self.vehi_app.handle_joystick_queue({"command": "set_forward", "speed": 150, "distance": 3000})

        if event.code in (ecodes.BTN_SOUTH, ecodes.BTN_A):  # 304 - drive backward
            self.vehi_app.handle_joystick_queue({"command": "set_backward", "speed": 150})

        elif event.code in (ecodes.BTN_WEST, ecodes.BTN_B):  # 305, 305
            instruction.update({"command": "set_forward_right", "speed": 150})
            self.vehi_app.handle_joystick_queue(instruction)

        elif event.code in (ecodes.BTN_EAST, ecodes.BTN_Y): # 308, 308
            instruction.update({"command": "set_forward_left", "speed": 150})
            self.vehi_app.handle_joystick_queue(instruction)

        elif event.code in (ecodes.BTN_TR, ecodes.BTN_TR2): # 311 , 313
            instruction.update({"left_speed": 150, "right_speed": 150})
            self.vehi_app.handle_joystick(instruction)

        elif event.code == ecodes.BTN_MODE:  # 316
            self.vehi_app.handle_instruction({"command": "exit"}, process=None)

        return None

    def run_event_loop(self, device_path: str, device_name: str):
        self.logger.info(f"Event loop active for: {device_name} ({device_path})")

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
                    self.logger.warning("Joystick disconnected unexpectedly!")
                    break

                if event is None:
                    continue

                self.print_device_events(event)

                if event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_Y:
                        self.axis_y = self.normalize_axis(event.value)
                        self.dispatch_movement()
                    elif event.code == ecodes.ABS_X:
                        self.axis_x = self.normalize_axis(event.value)
                        self.dispatch_movement()
                    elif event.code == ecodes.ABS_HAT0X:
                        self.logger.info(f"ABS_HAT0X Trigger value: {event.value}")
                        if event.value == -1:  # Left
                            self.vehi_app.handle_joystick({"command": "set_joystick", "left_speed": 150, "right_speed": -150})
                        elif event.value == 1:  # Right
                            self.vehi_app.handle_joystick({"command": "set_joystick", "left_speed": -150, "right_speed": 150})
                        else:
                            self.vehi_app.handle_instruction({"command": "set_stop"}, process=None) # 0 = release button
                    elif event.code == ecodes.ABS_HAT0Y:
                        self.logger.info(f"ABS_HAT0Y Trigger value: {event.value}")
                        if event.value == -1: # up button
                            self.vehi_app.handle_joystick({"command": "set_joystick", "left_speed": 150, "right_speed": 150})
                        elif event.value == 1: # down button
                            self.vehi_app.handle_joystick({"command": "set_joystick", "left_speed": -150, "right_speed": -150})
                        else:
                            self.vehi_app.handle_instruction({"command": "set_stop"}, process=None)

                elif event.type == ecodes.EV_KEY:
                    self.dispatch_button_action(event)

        except Exception as e:
            self.logger.warning(f"Joystick loop encountered error: {e}")
        finally:
            self.logger.info("Joystick event loop terminated")

    def connect_joystick(self):
        device_path, device_name = self.find_gamepad_path(self.device_path)
        if device_name is not None:
            self.logger.info(f"Locked onto Gamepad: {device_name} ({device_path})")
            return device_path, device_name
        self.logger.warning("No gamepad found. Retrying...")
        return None, None

    def _service_loop(self):
        while self.is_running:
            device_path, device_name = self.connect_joystick()
            if not self.is_running:
                break

            if self.device is not None and self.device.fd != -1:
                self.thread = threading.Thread(
                    target=self.run_event_loop,
                    name="JoystickVehicleDriver",
                    daemon=True,
                    args=(device_path, device_name),
                )
                self.thread.start()

                while self.is_running and self.thread.is_alive():
                    self.thread.join(timeout=0.2)

                if not self.is_running:
                    break

                if self.device:
                    try:
                        self.device.close()
                    except Exception:
                        pass
                    self.device = None
                self.thread = None
            else:
                self._stop_event.wait(2.0)

    def start(self):
        self.logger.info("Enter start JoystickAdapter service")
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()
        self.axis_x = 0.0
        self.axis_y = 0.0
        self.last_instruction = "none"

        if self.device is not None:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None

        self.service_thread = threading.Thread(
            target=self._service_loop, name="JoystickService", daemon=True
        )
        self.service_thread.start()
        self.logger.info("JoystickAdapter service started asynchronously")

    def stop(self):
        self.is_running = False
        self._stop_event.set()

        if self.device:
            try:
                self.device.close()
            except Exception:
                pass

        if self.service_thread and self.service_thread.is_alive():
            self.service_thread.join(timeout=1.0)

        self.vehi_app.handle_instruction({"command": "set_stop"}, process=None)
        self.logger.info("JoystickAdapter stopped cleanly")

    def print_device_events(self, event):
        if event.type == ecodes.EV_KEY:
            key_name = ecodes.KEY.get(event.code, f"KEY_{event.code}")
    
            if event.value == 1:
                state = "PRESSED"
            elif event.value == 0:
                state = "RELEASED"
            else:
                state = f"VALUE={event.value}"
    
            print(
                f"BUTTON: code={event.code:3d} "
                f"name={key_name:20s} {state}"
            )
    
        elif event.type == ecodes.EV_ABS:
            abs_name = ecodes.ABS.get(event.code, f"ABS_{event.code}")
    
            print(
                f"AXIS:   code={event.code:3d} "
                f"name={abs_name:10s} value={event.value}"
            )