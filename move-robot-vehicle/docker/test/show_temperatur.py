import time
import logging
from icm20948 import ICM20948

logging.basicConfig(level=logging.INFO)

imu = ICM20948()
logging.info("show temperatur")
while True:
    """Read a temperature in degrees C."""
    logging.info(imu.read_temperature())
    time.sleep(1)
