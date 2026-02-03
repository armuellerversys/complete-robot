#!/usr/bin/env python

import time
import threading
from matrix11x7 import Matrix11x7
from matrix11x7.fonts import font5x7 as font5x7
from core_utils import CoreUtils
from robot_imu import RobotImu
from magnetometer import Magnetometer

class MatrixDisplay:
    def __init__(self):
      self.matrix11x7 = Matrix11x7(None, 0x77)
      self.matrix11x7.set_brightness(0.5)
      #self.logger = CoreUtils.getLogger("matrix_display")
      self.imu = RobotImu()

    def showTemperatur(self):
        temperature = self.imu.read_temperature()
        #self.logger.debug("Temperature {}".format(round(temperature)))
        self.showString(str(round(temperature)))

    def showMagnetometerAngle(self):
        magnetometer = Magnetometer()
        self.showString(str(magnetometer.showData()))

    def showClock(self):
        # Create an Event object
        #stop_event = threading.Event()
        #t1 = threading.Thread(name="ShowMatrix", target=self.showClock_thread, args=(stop_event,)) 
       # t1.start()
       # return stop_event
     
    #def showClock_thread(self, stop_event):
        #self.logger.debug('[showClock]::Started')
        # Avoid retina-searage!
        self.matrix11x7.set_brightness(0.5)

        self.matrix11x7.rotate(270)

        #while not stop_event.is_set():
        self.matrix11x7.clear()

        # See https://docs.python.org/2/library/time.html
        # for more information on what the time formats below do.

        # Display the hour as two digits
        self.matrix11x7.write_string(
            time.strftime("%H"),
            x=0,
            y=0,
            font=font5x7)

        # Display the minute as two digits
        self.matrix11x7.write_string(
            time.strftime("%M"),
            x=0,
            y=6,
            font=font5x7)

        # Display the second as two digits
        #self.matrix11x7.write_string(
        #    time.strftime("%S"),
        #    x=0,
        #    y=12,
        #    font=font5x7)
        #self.logger.debug("Show clock")
        self.matrix11x7.show()
        time.sleep(0.5)

    def showString(self, text):
        #self.logger.debug(f"Show String: {text}")
        self.matrix11x7.clear()
        self.matrix11x7.write_string(text)
        # Show the buffer
        self.matrix11x7.show()

