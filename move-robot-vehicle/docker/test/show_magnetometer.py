import time
import logging
from icm20948 import ICM20948

logging.basicConfig(level=logging.INFO)

imu = ICM20948()

while True:
    mag_x, mag_y, mag_z = imu.read_magnetometer_data()
    logging.info("mag.x {}".format(mag_x))
    logging.info("mag.y {}".format(mag_y))
    logging.info("mag.z {}".format(mag_z))
    time.sleep(1)