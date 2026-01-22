from Raspi_MotorHAT import Raspi_MotorHAT
from gpiozero import DistanceSensor, RotaryEncoder, devices
import leds_led_shim
import signal
from core_utils import CoreUtils

class Robot:

    MOTOR_ADDRESS_I2C = 0x64
    wheel_diameter_mm = 60.0
    ticks_per_revolution = 624
    wheel_distance_mm = 132.0
    def __init__(self, motorhat_addr=MOTOR_ADDRESS_I2C):
        
        self.logger = CoreUtils.getLogger("Robot")
        
        # release GPIO
        devices._shutdown()
        # Setup the motorhat with the passed in address
        self._mh = Raspi_MotorHAT(addr=motorhat_addr)
    
        self.left_motor = self._mh.getMotor(1)
        self.right_motor  = self._mh.getMotor(2)

        LEFT_DISTANCE_ECHO = 17
        LEFT_DISTANCE_TRIGGER = 27
        RIGHT_DISTANCE_ECHO = 5
        RIGHT_DISTANCE_TRIGGER = 6
        FRONT_DISTANCE_ECHO = 22
        FRONT_DISTANCE_TRIGGER = 23

        # Device.pin_factory = PiGPIOFactory()
        self.left_distance_sensor = DistanceSensor(echo=LEFT_DISTANCE_ECHO, trigger=LEFT_DISTANCE_TRIGGER, queue_len=2, max_distance=1.0)
        self.right_distance_sensor = DistanceSensor(echo=RIGHT_DISTANCE_ECHO, trigger=RIGHT_DISTANCE_TRIGGER, queue_len=2, max_distance=1.0)
        self.front_distance_sensor = DistanceSensor(echo=FRONT_DISTANCE_ECHO, trigger=FRONT_DISTANCE_TRIGGER, queue_len=2, max_distance=1.0)
        # Define the GPIO pins for the encoders (adjust these to your wiring)
        LEFT_ENCODER_PIN_A = 16 # Example GPIO pin
        LEFT_ENCODER_PIN_B = 19 # Example GPIO pin
        RIGHT_ENCODER_PIN_A = 21 # Example GPIO pin
        RIGHT_ENCODER_PIN_B = 20 # Example GPIO pin
        self.right_encoder = RotaryEncoder(a=RIGHT_ENCODER_PIN_A, b=RIGHT_ENCODER_PIN_B, max_steps=0)
        self.left_encoder = RotaryEncoder(a=LEFT_ENCODER_PIN_A, b=LEFT_ENCODER_PIN_B, max_steps=0)

        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)

        # Setup the Leds
        self.leds = leds_led_shim.Leds()

        self.logger.debug('Robot created and initialized')
        # ensure the motors get stopped when the code exits
        # atexit.register(self.stop_all)

    def cleanup(sig, parm1, parm2):
        CoreUtils.getLogger("Robot").debug('Robot cleanup')
        devices._shutdown()

    def convert_speed(self, speed):
        # Choose the running mode
        mode = Raspi_MotorHAT.RELEASE
        if speed > 0:
            mode = Raspi_MotorHAT.FORWARD
        elif speed < 0:
            mode = Raspi_MotorHAT.BACKWARD

        # Scale the speed
        output_speed = (abs(speed) * 255) // 100
        return mode, int(output_speed)

    def set_left(self, speed):
        mode, output_speed = self.convert_speed(speed)
        self.logger.debug(f"Left-speed: {output_speed:.2f}")
        self.left_motor.setSpeed(output_speed)
        self.left_motor.run(mode)

    def set_right(self, speed):
        mode, output_speed = self.convert_speed(speed)
        self.logger.debug(f"Right-speed: {output_speed:.2f}")
        self.right_motor.setSpeed(output_speed)
        self.right_motor.run(mode)

    def stop_motors(self):
        self.logger.debug('Robot-stop_motors')
        self.left_motor.run(Raspi_MotorHAT.RELEASE)
        self.right_motor.run(Raspi_MotorHAT.RELEASE)

    def stop_motor_left(self):
        self.logger.debug('Robot-release-left-motor')
        self.left_motor.run(Raspi_MotorHAT.RELEASE)

    def stop_motor_right(self):
        self.logger.debug('Robot-release-right-motor')
        self.right_motor.run(Raspi_MotorHAT.RELEASE)

    def left_motor(self):
        return self.left_motor

    def right_motor(self):
        return self.right_motor

    def stop_all(self):
        print('Robot-stop_all')
        self.stop_motors()

        # Clear the display
        self.leds.clear()

        # reset sensors
        devices._shutdown()

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
    def set_green_one():
        leds = leds_led_shim.Leds().set_green_one()
