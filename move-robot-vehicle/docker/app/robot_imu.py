from icm20948 import ICM20948
from vpython import vector


class RobotImu:
    """Define a common interface to an inertial measurement unit with temperature"""
    def __init__(self):
        self._imu = ICM20948()

    def read_temperature(self):
        """Read a temperature in degrees C."""
        return self._imu.read_temperature()

    def read_gyroscope_vector(self):
        """Return prescaled gyro data"""
        _, _, _, x, y, z = self._imu.read_accelerometer_gyro_data()
        return vector(x, y, z)
    
    def read_gyroscope_data(self):
        """Return prescaled gyro data"""
        _, _, _, x, y, z = self._imu.read_accelerometer_gyro_data()
        return x, y, z 

    def read_accelerometer_vector(self):
        """Return accelerometer data"""
        accel_x, accel_y, accel_z, _, _, _ = self._imu.read_accelerometer_gyro_data()
        return vector(accel_x, accel_y, accel_z)
    
    def read_accelerometer_data(self):
        """Return accelerometer data"""
        accel_x, accel_y, accel_z, _, _, _ = self._imu.read_accelerometer_gyro_data()
        return accel_x, accel_y, accel_z
    
    def read_magnetometer_vector(self):
        """Return magnetometer data"""
        mag_x, mag_y, mag_z = self._imu.read_magnetometer_data()
        return vector(mag_x, -mag_y, -mag_z)

    def read_magnetometer_data(self):
            """Return magnetometer data"""
            return self._imu.read_magnetometer_data()
