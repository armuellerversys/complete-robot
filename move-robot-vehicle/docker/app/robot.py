from gpiozero import DistanceSensor, RotaryEncoder, devices
import leds_led_shim
import signal
import os
from core_utils import CoreUtils

# Ensure gpiozero uses the modern lgpio factory if not set in Docker
if 'GPIOZERO_PIN_FACTORY' not in os.environ:
    os.environ['GPIOZERO_PIN_FACTORY'] = 'lgpio'

shutdown_done = False

class Robot:
    MOTOR_ADDRESS_I2C = 0x64
    wheel_diameter_mm = 60.0
    ticks_per_revolution = 624
    wheel_distance_mm = 132.0

    def __init__(self, motorhat_addr=MOTOR_ADDRESS_I2C):
        self.logger = CoreUtils.getLogger("Robot")
        
        # Clean shutdown of any previous GPIO sessions
        devices._shutdown()

        # 1. Setup MotorHAT
        #self._mh = Raspi_MotorHAT(addr=motorhat_addr)
        #self._left_motor_obj = self._mh.getMotor(1)  # Renamed to avoid method collision
        #self._right_motor_obj = self._mh.getMotor(2)

        # 2. Setup Sensors (gpiozero uses lgpio automatically now)
        self.left_distance_sensor = DistanceSensor(echo=17, trigger=27, queue_len=2, max_distance=1.0)
        self.right_distance_sensor = DistanceSensor(echo=5, trigger=6, queue_len=2, max_distance=1.0)
        self.front_distance_sensor = DistanceSensor(echo=22, trigger=23, queue_len=2, max_distance=1.0)
        
        self.left_encoder = RotaryEncoder(a=16, b=19, max_steps=0)
        self.right_encoder = RotaryEncoder(a=21, b=20, max_steps=0)

        # 3. Setup LEDs
        self.leds = leds_led_shim.Leds()

        # 4. Handle OS Signals for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_exit_signal)
        signal.signal(signal.SIGTERM, self.handle_exit_signal)

        self.logger.debug('Robot created and initialized with lgpio backend')

    def handle_exit_signal(self, signum, frame):
        self.logger.info(f"Signal {signum} received. Cleaning up...")
        # self.stop_all()
        # exit(0)

    def stop_all(self):
        self.logger.debug('Robot-stop_all')
        self.leds.clear()
        Robot.safe_shutdown_devices()

    @staticmethod
    def safe_shutdown_devices():
        global shutdown_done
        if shutdown_done:
            return
        try:
            devices._shutdown()
        except Exception as ex:
            CoreUtils.getLogger("Robot").debug(f"Ignoring shutdown error: {ex}")
        finally:
            shutdown_done = True

    def set_forward_direction(self):
        self.servos.set_forward_direction()

    def set_led_red(self):
        self.leds.showRed()

    def set_led_blue(self):
        self.leds.showBlue()

    def set_led_green(self):
        self.leds.showGreen()
    
    def set_led_pink(self):
        self.leds.showPink()

    def set_led_purple(self):
        self.leds.showPurple()

    def set_led_yellow(self):
        self.leds.showYellow()

    def clear_led(self):
        self.leds.clear()

    @staticmethod
    def set_led_orange():
        led = leds_led_shim.Leds().showOrange()

    @staticmethod
    def set_led_white():
        leds_led_shim.Leds().showWhite()

    @staticmethod
    def set_led_green():
        leds_led_shim.Leds().showGreen()

    @staticmethod
    def set_led_blue():
        leds_led_shim.Leds().showBlue()

    @staticmethod
    def set_green_one():
        leds = leds_led_shim.Leds().set_green_one()
