
import logging
from time import sleep
import traceback
from gpiozero import devices
from gpiozero import RotaryEncoder
from leds_led_shim import Leds
from core_utils import CoreUtils

#import debugpy

#debugpy.listen(('0.0.0.0', 5678))

#input('Hello! Start testing Distance-Sensor\n')

ticks_to_mm_const = 3.2
logger = CoreUtils.getLogger("test encoder")

devices._shutdown()

leds = Leds()

LEFT_ENCODER_PIN_A = 16 # Example GPIO pin
LEFT_ENCODER_PIN_B = 19 # Example GPIO pin
RIGHT_ENCODER_PIN_A = 21 # Example GPIO pin
RIGHT_ENCODER_PIN_B = 20 # Example GPIO pin

# Initialize the RotaryEncoder for the encoders
# The Hall encoder generates pulses (counts) as the wheel turns.
right_encoder = RotaryEncoder(a=RIGHT_ENCODER_PIN_A, b=RIGHT_ENCODER_PIN_B, max_steps=0)
left_encoder = RotaryEncoder(a=LEFT_ENCODER_PIN_A, b=LEFT_ENCODER_PIN_B, max_steps=0)
logger.debug("move encoder: exit init forward behavior")

left_count_old = abs(left_encoder.steps)
right_count_old = abs(right_encoder.steps)
leds.showGreen()
try:
    while True:
        left_counts = abs(left_encoder.steps)
        right_counts = abs(right_encoder.steps)
        distance_tiks = (left_counts + right_counts) / 2
    
        logger.info(f"Right: {right_counts} - Left: {left_counts} - Distance in mm: {str(distance_tiks * ticks_to_mm_const)}")
        if (left_counts > left_count_old):
            leds.showPink()
        if (right_counts > right_count_old):
            leds.showOrange()
        left_count_old = left_counts
        right_count_old = right_counts
        sleep(600/1000)
        leds.showGreen()
except Exception:
    logger.debug(traceback.format_exc())
finally:
    logger.debug("close all")
    leds.clear()
    devices._shutdown()