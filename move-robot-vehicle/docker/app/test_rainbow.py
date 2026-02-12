from time import sleep
import leds_led_shim
import colorsys
import traceback
from core_utils import CoreUtils

def show_rainbow(leds):
    led_range = list(range(leds.count))
    hue_step = 1.0 / len(led_range)
    for index, led_address in enumerate(range(leds.count)):
        hue = hue_step * index
        rgb = colorsys.hsv_to_rgb(hue, 1.0, 0.6)
        rgb = [int(c*255) for c in rgb]
        leds.set_one(led_address, rgb)

logger = CoreUtils.getLogger("test rainbow")
leds = leds_led_shim.Leds()
try:
    while True:
        logger.info("LED on")
        show_rainbow(leds)
        leds.show()
        sleep(0.5)
        logger.info("off")
        leds.clear()
        leds.show()
        sleep(0.5)
except KeyboardInterrupt:
     logger.error(traceback.format_exc())
finally:
      logger.info("close all")
      leds.clear()
