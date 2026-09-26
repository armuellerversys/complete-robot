import os
import time
import threading
import glob
from evdev import InputDevice, ecodes
import debugpy
debugpy.listen(('0.0.0.0', 5678))

# Axis normalization configuration
AXIS_MAX = 32767
DEADZONE = 0.15

class CoreUtils:
    @staticmethod
    def getLogger(name):
        import logging
        logger = logging.getLogger(name)
        if not logger.handlers:
            # Configure logger only if it hasn't been configured yet
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        return logger

class JoystickAdapter:
    def __init__(self, vehi_app, devicePath="/dev/input/event5"):
        self.vehi_app = vehi_app
        self.logger = CoreUtils.getLogger(__name__)

        self.running = False
        self.thread = None

        self.categorize = None # For event categorization

        self.device_path = devicePath

        self.device = None

        self.instruction = {'command': 'set_stop'}

        # State tracking for steering (X) and throttle (Y)
        self.axis_x = 0.0
        self.axis_y = 0.0
        self.is_running = True

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
        if device_path and os.path.exists(device_path):
            try:
                device = InputDevice(device_path)
                capabilities = device.capabilities()
                if ecodes.EV_ABS in capabilities and ecodes.EV_KEY in capabilities:
                    return device_path, device.name
            except (PermissionError, FileNotFoundError, OSError):
                self.logger.warning(f"Cannot access {device_path}. Ensure proper permissions or run as root.")
                return None, None
        else:    
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
        if self.axis_y == 0.0 and self.axis_x == 0.0:
            self.instruction = {'command': 'set_stop'}
        # Forward Movement
        elif self.axis_y < 0:
            self.logger.debug(f"Dispatching movement: axis_x={self.axis_x}, axis_y={self.axis_y}, speed_x={speed_x}, speed_y={speed_y}")
            if self.axis_x < -triggerLevel:
                self.instruction = {'command': 'set_joystick', 'left_speed': (speed_y * -1), 'right_speed': (speed_x * -1)}
            elif self.axis_x > triggerLevel:
                self.instruction = {'command': 'set_joystick', 'left_speed': (speed_y * -1), 'right_speed': speed_x}
        
        # Backward Movement
        elif self.axis_y > 0:
            self.logger.debug(f"Dispatching movement: axis_x={self.axis_x}, axis_y={self.axis_y}, speed_x={speed_x}, speed_y={speed_y}")
            if self.axis_x < -triggerLevel:
                self.instruction = {'command': 'set_joystick', 'left_speed': speed_y, 'right_speed': (speed_x * -1)}
            elif self.axis_x > triggerLevel:
                self.instruction = {'command': 'set_joystick', 'left_speed': speed_y, 'right_speed': speed_x}
            
        if self.instruction is not None:        
            self.logger.debug(f"Dispatching instruction: {self.instruction}")
            self.vehi_app.handle_joystick(self.instruction)

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
        self.logger.info("Docker Gamepad Controller Service started. Waiting for Bluetooth joystick...")

        while self.is_running:
            device_path, device_name = self.find_gamepad_path(self.device_path)
            self.logger.info(f"Found Gamepad: {device_name} at {device_path}")

            if device_path:
                try:
                    self.running = True
                    
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

    def stop(self):
        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=1.0)

        self._send_stop()

        self.logger.info("JoystickAdapter stopped")

class VehicleApp:
    def __init__(self):
        self.forward_distance = 0
        self.last_time = time.time()

        self._sensor_mid = None
        self._sensor_left = None
        self._sensor_right = None

        # Initialize the joystick adapter
        joystick = JoystickAdapter(
            self,
            devicePath="/dev/input/event5",
        )

        joystick.start()

        print("VehicleApp: Initialization completed")

    @property
    def sensor_mid(self):
        return self._sensor_mid

    @property
    def sensor_left(self):
        return self._sensor_left  

    @property
    def sensor_right(self):
        return self._sensor_right   

    def handle_instruction(self, instruction, process):
        command = instruction['command']
        print(f"VehicleApp: Received command: {command}")

    def handle_joystick(self, instruction):
        command = instruction['command']
        print(f"VehicleApp: Received joystick command: {command}")
        if command == 'set_joystick':
            left_speed = instruction.get('left_speed', 0)
            right_speed = instruction.get('right_speed', 0)
            print(f"VehicleApp: Setting left speed to {left_speed}, right speed to {right_speed}")
        elif command == 'set_stop':
            print("VehicleApp: Stopping vehicle")



if __name__ == "__main__":
   
    print("Starting VehicleApp with JoystickAdapter...")
    # Initialize the vehicle application
    vehi_app = VehicleApp()

    # Create the joystick adapter with the vehicle app
    joystick_adapter = JoystickAdapter(vehi_app)

    try:
        # Start the joystick adapter
        print("Starting JoystickAdapter...")

        joystick_adapter.start()
    except KeyboardInterrupt:
        # Gracefully stop on Ctrl+C
        joystick_adapter.stop()


