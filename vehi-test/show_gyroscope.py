import time
import logging
from icm20948 import ICM20948

logging.basicConfig(level=logging.INFO)

imu = ICM20948()

while True:
    accel_x, accel_y, accel_z, _, _, _ = imu.read_accelerometer_gyro_data()
    logging.info("gyro.x {}".format(accel_x))
    logging.info("gyro.y {}".format(accel_y))
    logging.info("gyro.z {}".format(accel_z))
    time.sleep(1)