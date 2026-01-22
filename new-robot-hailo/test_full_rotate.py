
from time import sleep
import traceback
from gpiozero import devices
from gpiozero import RotaryEncoder
from Raspi_MotorHAT import Raspi_MotorHAT
from leds_led_shim import Leds
from core_utils import CoreUtils

#import debugpy

#debugpy.listen(('0.0.0.0', 5678))

#input('Hello! Start testing Distance-Sensor\n')

ticks_to_mm_const = 3.2
logger = CoreUtils.getLogger("test encoder-motor")

devices._shutdown()

leds = Leds()

LEFT_ENCODER_PIN_A = 16 # Example GPIO pin
LEFT_ENCODER_PIN_B = 19 # Example GPIO pin
RIGHT_ENCODER_PIN_A = 21 # Example GPIO pin
RIGHT_ENCODER_PIN_B = 20 # Example GPIO pin
ROTATE_SPEED = 200
ROTATE_STEPS = 900

devices._shutdown()
# Initialize the RotaryEncoder for the encoders
# The Hall encoder generates pulses (counts) as the wheel turns.
right_encoder = RotaryEncoder(a=RIGHT_ENCODER_PIN_A, b=RIGHT_ENCODER_PIN_B, max_steps=0)
left_encoder = RotaryEncoder(a=LEFT_ENCODER_PIN_A, b=LEFT_ENCODER_PIN_B, max_steps=0)

mh = Raspi_MotorHAT(addr=0x64)
lm = mh.getMotor(1)
rm = mh.getMotor(2)

leds.showGreen()
try:
    logger.debug("rotate once right")
    # rotate right motor
    rm.setSpeed(ROTATE_SPEED)
    rm.run(Raspi_MotorHAT.FORWARD)

    logger.debug(f"Running right motor {ROTATE_STEPS} steps...")
    while True:
        leds.showBlue()
        if (right_encoder.steps > ROTATE_STEPS):
                break
    rm.run(Raspi_MotorHAT.RELEASE)
    
    leds.showGreen()
    sleep(900/1000)

    logger.debug("rotate once left")
    # rotate left motor
    lm.setSpeed(ROTATE_SPEED)
    lm.run(Raspi_MotorHAT.FORWARD)

    logger.debug(f"Running left motor {ROTATE_STEPS} steps...")
    while True:
        leds.showRed()
        if (left_encoder.steps > ROTATE_STEPS):
                break
    lm.run(Raspi_MotorHAT.RELEASE) 
    leds.showGreen()

except Exception:
    logger.debug(traceback.format_exc())
finally:
    logger.debug("close all")
    leds.clear()
    devices._shutdown()