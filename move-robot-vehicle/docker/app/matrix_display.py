#!/usr/bin/env python
import threading
import requests
import json
from core_utils import CoreUtils
from robot_imu import RobotImu
from magnetometer import Magnetometer

URL = "http://192.168.4.1:5000/showChar"

# The headers specify that you are sending JSON data
headers = {"Content-Type": "application/json"}

class MatrixDisplay:   

    def __init__(self):
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

    def showString(self, text):
        """The actual workhorse method"""
        self.logger.debug(f"Show String: {text}")
        # Optional: Stop any existing scrolling thread before starting a new one
        self._stop_event.set() 
        self.showString_async(text)

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

    def showString_async(self, text):
        """Launches showString in a background thread"""
        self._stop_event = threading.Event()
        self.display_thread = threading.Thread(
            target=self.show_text, 
            args=(text,), 
            daemon=True # Daemon ensures thread dies if main program exits
        )
        self.display_thread.start()

    def show_text(self, text):
      
        #curl -X POST http://192.168.4.1:5000/showChar -H "Content-Type: application/json" \-d '{"message": "This is a test"}'
        try:
            # Create the data payload as a dictionary
            payload = {"message": text}

            # Send a POST request to the server with the JSON data
            self.logger.info(f"Sending request to {URL}...")
            response = requests.post(URL, data=json.dumps(payload), headers=headers, timeout=1)

            # Check if the request was successful
            if response.status_code == 200:
                self.logger.info("Success! The matrix server received the request.")
                self.logger.info("Matrix Server response:", response.json())
            else:
                self.logger.error(f"Matrix Server Error! Status code: {response.status_code} - {response.text}")

        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Failed to connect to the Matrix Server at {URL}.")
            self.logger.error(f"Error details: {e}")
