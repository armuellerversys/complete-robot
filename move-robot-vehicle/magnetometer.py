#!/usr/bin/env python

import math

from icm20948 import ICM20948
from core_utils import CoreUtils

print("""magnetometer.py - Convert raw values to heading

Rotate the sensor (X-axis upwards) through 360 degrees to calibrate.

Press Ctrl+C to exit!

""")

X = 0
Y = 1
Z = 2

# The two axes which relate to heading, depends on orientation of the sensor
# Think Left & Right, Forwards and Back, ignoring Up and Down
AXES = Y, Z
class Magnetometer:
    def __init__(self):
        # Initialise the imu
        self.imu = ICM20948()

        # Store an initial two readings from the Magnetometer
        self.amin = list(self.imu.read_magnetometer_data())
        self.amax = list(self.imu.read_magnetometer_data())

        self.logger = CoreUtils.getLogger("magnetometer_display")

    def showData(self):
        # Read the current, uncalibrated, X, Y & Z magnetic values from the magnetometer and save as a list
        mag = list(self.imu.read_magnetometer_data())

        # Step through each uncalibrated X, Y & Z magnetic value and calibrate them the best we can
        for i in range(3):
            v = mag[i]
            # If our current reading (mag) is less than our stored minimum reading (amin), then save a new minimum reading
            # ie save a new lowest possible value for our calibration of this axis
            if v < self.amin[i]:
                self.amin[i] = v
            # If our current reading (mag) is greater than our stored maximum reading (amax), then save a new maximum reading
            # ie save a new highest possible value for our calibration of this axis
            if v > self.amax[i]:
                self.amax[i] = v

            # Calibrate value by removing any offset when compared to the lowest reading seen for this axes
            mag[i] -= self.amin[i]

            # Scale value based on the highest range of values seen for this axes
            # Creates a calibrated value between 0 and 1 representing magnetic value
            try:
                mag[i] /= self.amax[i] - self.amin[i]
            except ZeroDivisionError:
                pass
            # Shift magnetic values to between -0.5 and 0.5 to enable the trig to work
            mag[i] -= 0.5

        # Convert from Gauss values in the appropriate 2 axis to a heading in Radians using trig
        # Note this does not compensate for tilt
        heading = math.atan2(
                mag[AXES[0]],
                mag[AXES[1]])

        # If heading is negative, convert to positive, 2 x pi is a full circle in Radians
        if heading < 0:
            heading += 2 * math.pi

        # Convert heading from Radians to Degrees
        heading = math.degrees(heading)
        # Round heading to nearest full degree
        heading = round(heading)

        # Note: Headings will not be correct until a full 360 deg calibration turn has been completed to generate amin and amax data
        self.logger.debug(f"Heading: {heading}")

        return heading

    ## ▶️ Main Execution
if __name__ == '__main__':
    magnetometer = Magnetometer()
    try:
        input('Hello! Start testing magnetometer:\n')
        # Create the controller instance
        magnetometer.showData()
    except KeyboardInterrupt:
        print("Bye")
