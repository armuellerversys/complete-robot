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
      self.logger = CoreUtils.getLogger("matrix_display")
      self.imu = RobotImu()

      # Track the current display thread to prevent overlapping
      self.display_thread = None
      self._stop_event = threading.Event()

    def showTemperature(self):
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
        """The actual workhorse method"""
        self.logger.debug(f"Show String: {text}")
        self.matrix11x7.clear()
        # Optional: Stop any existing scrolling thread before starting a new one
        self._stop_event.set() 
        # If the text is long, use the library's scroll function
        if len(text) > 2:
            # Note: ensure your library's scroll_text doesn't block forever
            # or wrap it in a loop that checks self._stop_event
            self.showString_async(text)
        else:
            self.matrix11x7.write_string(text)
            self.matrix11x7.show()

    def showString_async(self, text):
        """Launches showString in a background thread"""
        self._stop_event = threading.Event()
        self.display_thread = threading.Thread(
            target=self.scroll_message, 
            args=(text,), 
            daemon=True # Daemon ensures thread dies if main program exits
        )
        self.display_thread.start()

    def scroll_message(self, message):
        self.matrix11x7.clear()                         # Clear the display and reset scrolling to (0, 0)
        length = self.matrix11x7.write_string(message)  # Write out your message
        self.matrix11x7.show()                          # Show the result
        time.sleep(0.5)                              # Initial delay before scrolling

        length -= self.matrix11x7.width

        # Now for the scrolling loop...
        while length > 0:
            self.matrix11x7.scroll(1)                   # Scroll the buffer one place to the left
            self.matrix11x7.show()                      # Show the result
            length -= 1
            time.sleep(1)                         # Delay for each scrolling step  

    def update_telemetry(self, heading, distance, status="OK"):
        """
        Displays a condensed version of the robot's state.
        Example: 'H140' -> Heading 140, 'D200' -> Distance 200
        """
        # Create a compact string
        # We use a leading char to identify the metric
        if status != "OK":
            self.showString_async(f"!!{status}!!") # Flash status if avoiding
        else:
            # Toggle display every few seconds or just show heading
            self.showString_async(f"H{int(heading)} D{int(distance)}")
