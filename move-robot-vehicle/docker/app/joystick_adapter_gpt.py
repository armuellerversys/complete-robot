import glob
import os
import select
import threading
import time

from evdev import InputDevice, categorize, ecodes

from core_utils import CoreUtils


# Axis normalization configuration
AXIS_MAX = 32767
DEADZONE = 0.15
TRIGGER_LEVEL = 0.3


class JoystickAdapter:
    """
    Adapter for an evdev gamepad.

    Threading model
    ---------------
    start()
        Starts a service thread and returns immediately.

    service thread
        Looks for the gamepad, starts the event thread, and reconnects
        when the gamepad is disconnected.

    event thread
        Reads and dispatches gamepad events.

    stop()
        Signals both threads to stop, closes the input device to unblock
        any pending I/O, waits for the threads, and finally stops the
        vehicle.

    This separation is important because start() must not block the
    Move_app worker thread.
    """

    def __init__(self, vehi_app, device_path="/dev/input/event5"):
        self.vehi_app = vehi_app
        self.logger = CoreUtils.getLogger(__name__)

        self.thread = None
        self.service_thread = None

        self.device_path = device_path
        self.device = None

        self.instruction = {'command': 'set_stop'}
        self.last_instruction = 'none'

        # State tracking for steering (X) and throttle (Y)
        self.axis_x = 0.0
        self.axis_y = 0.0

        self.is_running = False
        self._stop_event = threading.Event()

        self.logger.info(
            f"JoystickAdapter initialized with default path: "
            f"{self.device_path}"
        )

    @staticmethod
    def normalize_axis(value: int) -> float:
        """Converts raw analog input (-32768 to 32767) to -1.0 .. 1.0."""
        norm = value / AXIS_MAX

        if abs(norm) < DEADZONE:
            return 0.0

        return norm

    @staticmethod
    def scale_speed(norm_val: float, max_speed: int = 200) -> int:
        """Scales normalized float (-1.0 to 1.0) to motor speed."""
        return int(abs(norm_val) * max_speed)

    def find_gamepad_path(self, target_path: str):
        """Scans /dev/input/event* to locate a suitable gamepad."""

        # Reuse current active connection if still valid.
        if (
            self.device is not None
            and self.device.fd != -1
            and target_path == self.device.path
        ):
            self.logger.info(
                f"Using previously connected gamepad: "
                f"{self.device.path} ({self.device.name})"
            )
            return self.device.path, self.device.name

        # Check explicitly provided target_path.
        if target_path and os.path.exists(target_path):
            try:
                self.logger.info(
                    f"Attempting connection to specified path: {target_path}"
                )

                dev = InputDevice(target_path)
                capabilities = dev.capabilities()

                if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                    self.device = dev

                    self.logger.info(
                        f"Found gamepad at path: "
                        f"{target_path} ({dev.name})"
                    )

                    return target_path, dev.name

                dev.close()

            except (PermissionError, FileNotFoundError, OSError) as err:
                self.logger.warning(
                    f"Cannot access {target_path}: {err}"
                )

        # Fall back to scanning all event nodes.
        for path in glob.glob('/dev/input/event*'):
            try:
                dev = InputDevice(path)
                capabilities = dev.capabilities()

                if (
                    ecodes.EV_ABS in capabilities
                    and ecodes.EV_KEY in capabilities
                ):
                    if "keyboard" not in dev.name.lower():
                        self.device = dev

                        self.logger.info(
                            f"Dynamically discovered gamepad at: "
                            f"{path} ({dev.name})"
                        )

                        return path, dev.name

                dev.close()

            except (PermissionError, FileNotFoundError, OSError):
                continue

        self.device = None
        return None, None

    def dispatch_movement(self):
        """Evaluates current X/Y axes and sends movement instructions."""

        speed_y = self.scale_speed(self.axis_y)
        speed_x = self.scale_speed(self.axis_x)

        # Center deadzone state: issue stop once when transitioning to rest.
        if self.axis_y == 0.0 and self.axis_x == 0.0:
            if self.last_instruction != 'set_stop':
                self.instruction = {'command': 'set_stop'}

                self.vehi_app.handle_instruction(
                    self.instruction,
                    process=None
                )

                self.last_instruction = 'set_stop'

            return

        instruction = {'command': 'set_joystick'}
        is_turning = abs(self.axis_x) > TRIGGER_LEVEL

        # Handle Forward / Reverse / Turning Logic.
        if self.axis_y < -TRIGGER_LEVEL:
            if is_turning:
                instruction.update({
                    'left_speed': speed_x,
                    'right_speed': speed_y
                })
            else:
                instruction.update({
                    'left_speed': speed_y,
                    'right_speed': speed_y
                })

        elif self.axis_y > TRIGGER_LEVEL:
            if is_turning:
                instruction.update({
                    'left_speed': -speed_x,
                    'right_speed': -speed_y
                })
            else:
                instruction.update({
                    'left_speed': -speed_y,
                    'right_speed': -speed_y
                })

        else:
            # Y is within central neutral band.
            if self.axis_x < -TRIGGER_LEVEL:
                # Turn Left on spot.
                instruction.update({
                    'left_speed': 0,
                    'right_speed': speed_x
                })

            elif self.axis_x > TRIGGER_LEVEL:
                # Turn Right on spot.
                instruction.update({
                    'left_speed': speed_x,
                    'right_speed': 0
                })

            else:
                return

        # Execute instruction.
        self.logger.debug(
            f"Dispatching movement: {instruction}"
        )

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

        self.logger.info(
            f"Button event: {key_event.keycode} - "
            f"State: {key_event.keystate}"
        )

        if key_event.keystate != key_event.key_down:
            return None

        instruction = {'command': 'set_joystick'}

        if event.code in (ecodes.BTN_NORTH, ecodes.BTN_X):
            self.logger.info("BTN_NORTH triggered via GPAD button")

            self.vehi_app.handle_instruction(
                {'command': 'set_stop'},
                process=None
            )

        elif event.code in (ecodes.BTN_SOUTH, ecodes.BTN_A):
            self.logger.info("BTN_SOUTH triggered via GPAD button")

            self.vehi_app.handle_instruction(
                {'command': 'set_stop'},
                process=None
            )

        elif event.code in (ecodes.BTN_EAST, ecodes.BTN_B):
            self.logger.info(
                "BTN_EAST triggered via GPAD button 305"
            )

            instruction.update({
                'left_speed': 150,
                'right_speed': -150
            })

            self.vehi_app.handle_joystick(instruction)

        elif event.code in (ecodes.BTN_WEST, ecodes.BTN_Y):
            self.logger.info(
                "BTN_WEST triggered via GPAD button"
            )

            instruction.update({
                'left_speed': -150,
                'right_speed': 150
            })

            self.vehi_app.handle_joystick(instruction)

        elif event.code == ecodes.BTN_TL:
            # Left trigger button 310.
            self.logger.info(
                "BTN_TL triggered via GPAD button"
            )

            instruction.update({
                'left_speed': -150,
                'right_speed': 150
            })

            self.vehi_app.handle_joystick(instruction)

        elif event.code == ecodes.BTN_TR:
            # Right trigger button 311.
            self.logger.info(
                "BTN_TR triggered via GPAD button"
            )

            instruction.update({
                'left_speed': 150,
                'right_speed': +150
            })

            self.vehi_app.handle_joystick(instruction)

        elif event.code == ecodes.BTN_TL2:
            # Left trigger button 312.
            self.logger.info(
                "BTN_TL2 triggered via GPAD button"
            )

            instruction.update({
                'left_speed': -150,
                'right_speed': 150
            })

            self.vehi_app.handle_joystick(instruction)

        elif event.code == ecodes.BTN_TR2:
            # Right trigger button 313.
            self.logger.info(
                "BTN_TR2 triggered via GPAD button"
            )

            instruction.update({
                'left_speed': 150,
                'right_speed': +150
            })

            self.vehi_app.handle_joystick(instruction)

        elif event.code == ecodes.BTN_Z:
            self.logger.info(
                "BTN_Z triggered via GPAD button"
            )

            self.vehi_app.handle_instruction(
                {'command': 'set_stop'},
                process=None
            )

        elif event.code == ecodes.BTN_MODE:
            self.logger.info(
                "BTN_MODE triggered via GPAD button"
            )

            self.vehi_app.handle_instruction(
                {'command': 'exit'},
                process=None
            )

        elif event.code == ecodes.BTN_SELECT:
            self.logger.info(
                "BTN_SELECT triggered via GPAD button"
            )

            self.vehi_app.handle_instruction(
                {'command': 'set_stop'},
                process=None
            )

        else:
            self.logger.info(
                "BTN_SELECT Exit instruction sent via Joystick"
            )

        return None

    def run_event_loop(self, device_path: str, device_name: str):
        """Processes incoming events from the connected gamepad."""

        self.logger.info(
            f"Connected event loop started: "
            f"{device_name} ({device_path})"
        )

        try:
            while self.is_running and self.device is not None:

                # Do not use InputDevice.read_loop() here.
                #
                # read_loop() can block indefinitely when the joystick
                # is idle. select() gives us a timeout so that the
                # shutdown flag can always be checked.
                try:
                    readable, _, _ = select.select(
                        [self.device.fd],
                        [],
                        [],
                        0.2
                    )

                except (OSError, ValueError):
                    # Device was closed or became invalid.
                    break

                if not self.is_running:
                    break

                if not readable:
                    continue

                try:
                    event = self.device.read_one()

                except (OSError, IOError):
                    self.logger.warning(
                        "Joystick disconnected during active read loop!"
                    )
                    break

                if event is None:
                    continue

                self.logger.info(
                    f"Event Type: {event.type}, "
                    f"Code: {event.code}, "
                    f"Value: {event.value}"
                )

                instruction = {'command': 'set_joystick'}

                # -------------------------------------------------
                # Analog stick movements
                # -------------------------------------------------
                if event.type == ecodes.EV_ABS:

                    if event.code == ecodes.ABS_Y:
                        self.axis_y = self.normalize_axis(event.value)
                        self.dispatch_movement()

                    elif event.code == ecodes.ABS_X:
                        self.axis_x = self.normalize_axis(event.value)
                        self.dispatch_movement()

                    if event.code == ecodes.ABS_RX:
                        self.axis_y = self.normalize_axis(event.value)
                        self.logger.info(
                            f"ABS_RX Analog stick value: {event.value}"
                        )

                    elif event.code == ecodes.ABS_RY:
                        self.axis_x = self.normalize_axis(event.value)
                        self.logger.info(
                            f"ABS_RY Analog stick value: {event.value}"
                        )

                    elif event.code == ecodes.ABS_HAT0X:
                        self.logger.info(
                            f"ABS_HAT0X Trigger value: {event.value}"
                        )

                        if event.value == -1:
                            instruction.update({
                                'left_speed': 150,
                                'right_speed': -150
                            })

                            self.vehi_app.handle_joystick(instruction)

                        elif event.value == 1:
                            instruction.update({
                                'left_speed': -150,
                                'right_speed': 150
                            })

                            self.vehi_app.handle_joystick(instruction)

                        elif event.value == 0:
                            self.vehi_app.handle_instruction(
                                {'command': 'set_stop'},
                                process=None
                            )

                    elif event.code == ecodes.ABS_HAT0Y:
                        self.logger.info(
                            f"ABS_HAT0Y Trigger value: {event.value}"
                        )

                        if event.value == -1:
                            instruction.update({
                                'left_speed': 150,
                                'right_speed': 150
                            })

                            self.vehi_app.handle_joystick(instruction)

                        elif event.value == 1:
                            instruction.update({
                                'left_speed': -150,
                                'right_speed': -150
                            })

                            self.vehi_app.handle_joystick(instruction)

                        elif event.value == 0:
                            self.vehi_app.handle_instruction(
                                {'command': 'set_stop'},
                                process=None
                            )

                    elif event.code == ecodes.BTN_TL:
                        self.logger.info(
                            f"BTN_TL Button value: {event.value}"
                        )

                        instruction.update({
                            'left_speed': 150,
                            'right_speed': -150
                        })

                        self.vehi_app.handle_joystick(instruction)

                    elif event.code == ecodes.BTN_TR:
                        self.logger.info(
                            f"BTN_TR Button value: {event.value}"
                        )

                        instruction.update({
                            'left_speed': -150,
                            'right_speed': 150
                        })

                        self.vehi_app.handle_joystick(instruction)

                    else:
                        self.logger.debug(
                            f"Unhandled ABS event {event}: "
                            f"Code {event.code}, Value {event.value}"
                        )

                # -------------------------------------------------
                # Button events
                # -------------------------------------------------
                elif event.type == ecodes.EV_KEY:
                    self.dispatch_button_action(event)

        except Exception as e:
            self.logger.warning(
                f"Joystick event loop terminated: {e}"
            )

        finally:
            self.logger.info(
                "Joystick event loop stopped"
            )

    def _service_loop(self):
        """
        Maintains the joystick connection.

        This method runs in the service thread. It is deliberately
        separate from start(), so start() can return immediately to
        the caller.
        """

        self.logger.info(
            f"Starting Gamepad Service. Target path: "
            f"{self.device_path}"
        )

        try:
            while self.is_running:

                device_path, device_name = self.connect_joystick()

                if not self.is_running:
                    break

                if (
                    self.device is not None
                    and self.device.fd != -1
                ):
                    self.logger.info(
                        f"Starting event loop thread for Gamepad: "
                        f"{self.device.name}"
                    )

                    self.thread = threading.Thread(
                        target=self.run_event_loop,
                        name="JoystickVehicleDriver",
                        daemon=True,
                        args=(device_path, device_name)
                    )

                    self.thread.start()

                    # Wait for the event thread to finish.
                    #
                    # A timeout is used so stop() can terminate the
                    # service immediately.
                    while (
                        self.is_running
                        and self.thread.is_alive()
                    ):
                        self.thread.join(timeout=0.2)

                    if not self.is_running:
                        break

                    self.logger.info(
                        "Joystick event thread stopped; "
                        "attempting reconnect..."
                    )

                    # Cleanup closed device before retry.
                    if self.device:
                        try:
                            self.device.close()
                        except Exception:
                            pass

                        self.device = None

                    self.thread = None

                else:
                    self.logger.info(
                        "No active gamepad. "
                        "Retrying connection in 2 seconds..."
                    )

                    # Event.wait() is interruptible by stop().
                    self._stop_event.wait(2.0)

        except Exception as e:
            self.logger.error(
                f"Joystick service terminated unexpectedly: {e}"
            )

        finally:
            self.logger.info(
                "Joystick service thread stopped"
            )

    def start(self):
        """
        Starts the joystick service and returns immediately.

        The previous implementation performed the complete reconnect
        loop directly inside start(), which blocked the Move_app worker.
        """

        if self.is_running:
            self.logger.info(
                "JoystickAdapter is already running"
            )
            return

        self.logger.info(
            f"Starting JoystickAdapter. "
            f"Target path: {self.device_path}"
        )

        self.is_running = True
        self._stop_event.clear()

        # Reset state from a previous run.
        self.axis_x = 0.0
        self.axis_y = 0.0
        self.last_instruction = 'none'

        # Make sure a stale device is not reused.
        if self.device is not None:
            try:
                self.device.close()
            except Exception:
                pass

            self.device = None

        self.service_thread = threading.Thread(
            target=self._service_loop,
            name="JoystickService",
            daemon=True
        )

        self.service_thread.start()

        # IMPORTANT:
        # Do not join here. start() must return to Move_app.
        self.logger.info(
            "JoystickAdapter started"
        )

    def connect_joystick(self):
        """Attempts to discover and lock onto an available joystick."""

        device_path, device_name = self.find_gamepad_path(
            self.device_path
        )

        if device_name is not None:
            self.logger.info(
                f"Successfully locked onto Gamepad: "
                f"{device_name} at {device_path}"
            )

            return device_path, device_name

        self.logger.warning(
            "No gamepad found. Waiting for device connection..."
        )

        return None, None

    def stop(self):
        """
        Stops the joystick service and waits for its threads to finish.

        Closing the evdev device is intentional: it wakes the event
        thread if it is currently waiting for input.
        """

        if not self.is_running:
            self.logger.info(
                "JoystickAdapter is already stopped"
            )
            return

        self.logger.info(
            "Stopping JoystickAdapter"
        )

        # Stop all loops.
        self.is_running = False
        self._stop_event.set()

        # Close the input device.
        #
        # This is important because the event thread may currently
        # be waiting for input.
        if self.device is not None:
            try:
                self.device.close()
            except Exception as e:
                self.logger.debug(
                    f"Error closing joystick device: {e}"
                )

            self.device = None

        # Wait for the event thread.
        if (
            self.thread is not None
            and self.thread.is_alive()
        ):
            self.thread.join(timeout=2.0)

        self.thread = None

        # Wait for the service thread.
        if (
            self.service_thread is not None
            and self.service_thread.is_alive()
        ):
            self.service_thread.join(timeout=2.0)

        self.service_thread = None

        # Stop vehicle.
        self.vehi_app.handle_instruction(
            {'command': 'set_stop'},
            process=None
        )

        self.logger.info(
            "JoystickAdapter successfully stopped."
        )
