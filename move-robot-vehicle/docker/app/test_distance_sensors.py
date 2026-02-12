from gpiozero import DistanceSensor, devices
from time import sleep
import traceback
from core_utils import CoreUtils
from leds_led_shim import Leds
from core_utils import CoreUtils
#import debugpy

#debugpy.listen(('0.0.0.0', 5678))

#input('Hello! Start testing Distance-Sensor\n')

logger = CoreUtils.getLogger("test_distance_sensor")
logger.info("start test_distance_sensors")

leds = Leds()

devices._shutdown()

sensor_l = DistanceSensor(echo=17, trigger=27, max_distance=1, threshold_distance=0.2)
sensor_r = DistanceSensor(echo=5, trigger=6, max_distance=1, threshold_distance=0.2)
sensor_m = DistanceSensor(echo=22, trigger=23, max_distance=1, threshold_distance=0.2)

l_distance_old = sensor_l.distance
r_distance_old = sensor_r.distance
m_distance_old = sensor_m.distance

leds.showGreen()
try:
    while True:
        l_distance = sensor_l.distance
        r_distance = sensor_r.distance
        m_distance = sensor_m.distance
        logger.info(f"Left: {l_distance*100:.2f} cm, Right: {r_distance*100:.2f} cm, Middle: {m_distance*100:.2f} cm")
        if (l_distance > l_distance_old):
            leds.showPurple()
        elif(r_distance > r_distance_old):
            leds.showRed()
        elif (m_distance > m_distance_old):
            leds.showBlue()
        l_distance_old = l_distance
        r_distance_old = r_distance
        m_distance_old = m_distance
        sleep(500/1000)
        leds.showGreen()
except Exception:
    logger.error(traceback.format_exc())
finally:
    logger.info("close all")
    leds.clear()
    devices._shutdown()