import time
import os, signal
import cv2
from robot import Robot
import logging
import camera_stream
import requests
import json
from matrix_display import MatrixDisplay
from pid_controller import PIController
from image_app_core import put_output_image
from move_motor import Move_motor

from image_app_core import clear_queue

##

# The URL of your Flask voice server
# Make sure to use the correct IP address and port
URL = "http://192.168.4.6:6000/say"

# The headers specify that you are sending JSON data
headers = {
    "Content-Type": "application/json"
}


class Move_app:
    def __init__(self):
        self.logger = self.getLogger()
        self.matrixDisplay = MatrixDisplay()
        # Set pan and tilt to middle, then clear it.
        self.robot = Robot()
        self.robot.set_pan(0)
        self.robot.set_tilt(0)
        
        # warm up and servo move time
        time.sleep(0.1)
        # Servo's will be in place - stop them for now.
        self.robot.servos.stop_all()
        print("Move_app:move setup Complete")
        self.logger.debug("Move_app:Move-app init completed")

    def find_object(self, original_frame):
        print("find_object")
        """Search the frame for an object. Return the rectangle of the largest by w * h"""
        gray_img = cv2.cvtColor(original_frame, cv2.COLOR_BGR2GRAY)
        objects = self.cascade.detectMultiScale(gray_img)
        largest = 0, (0, 0, 0, 0)  # area, x, y, w, h
        for (x, y, w, h) in objects:
            item_area = w * h
            if item_area > largest[0]:
                largest = item_area, (x, y, w, h)
        return largest[1]

    def initCamera(self):
        print("Init camera")
        ## cascade_path = "/usr/local/lib/python3.7/dist-packages/cv2/data/haarcascade_frontalface_default.xml"
        cascade_path = "/usr/local/lib/python3.11/dist-packages/cv2/data/haarcascade_frontalcatface.xml"
        assert os.path.exists(cascade_path), f"File {cascade_path} not found"
        self.cascade = cv2.CascadeClassifier(cascade_path)
        # Tuning values
        self.center_x = 160
        self.center_y = 120
        self.min_size = 20
        self.pan_pid = PIController(proportional_constant=0.1, integral_constant=0.03)
        self.tilt_pid = PIController(proportional_constant=-0.1, integral_constant=-0.03)
        self.camera = camera_stream.setup_camera()           

    def exit_server(self, server):
        if server and server.is_alive():
            print(f"Move_app:Sending SIGINT to PID {server.pid}...")
            os.kill(server.pid, signal.SIGINT)  # graceful shutdown
            server.join(timeout=3)

            # Fallback in case SIGINT didn't work
            if server.is_alive():
                print("Move_app:SIGINT failed, force terminating...")
                server.terminate()
                server.join()
            self.matrixDisplay.showClock()
            print("Server stopped cleanly.")
        else:
            print("Server not running.")

    def handle_instruction(self, instruction, process):
      command = instruction['command']
      self.logger.debug(f"Command: {command}")
      type = "-"
      if command == "set_left":
        type = "L"
        self.robot.stop_motor_left()
        left_instr = int(instruction['speed'])
        self.robot.set_left(left_instr)
        self.robot.set_led_red()
        self.logger.debug(f"Move_app:Left-speed: {left_instr:.2f}")
      elif command == "set_right":
        type = "R"
        self.robot.stop_motor_right()
        right_instr = int(instruction['speed'])
        self.robot.set_right(right_instr)
        self.robot.set_led_red()
        self.logger.debug(f"Move_app:Right-speed: {right_instr:.2f}")
      elif command == "set_backward":
         print("backward")
         type = "B"
         move_motor = Move_motor()
         move_motor.run_backward()
         self.robot.set_led_red()
         self.logger.debug(f"backward-run")
      elif command == "set_forward":
         print("forward")
         type = "F"
         move_motor = Move_motor()
         move_motor.run_forward()
         self.robot.set_led_red()
         self.logger.debug(f"Move_app:Forward-run")
      elif command == "set_stop":
         print("stopping")
         type = "S"
         move_motor = Move_motor()
         move_motor.turn_off_motors()
         clear_queue()
         self.robot.set_led_blue()
         self.logger.debug(f"Move_app:Stop-run")
      elif command == "exit":
         print("Move_app:exiting")
         type = "X"
         self.camera.close()
         self.robot.set_led_blue()
         self.logger.debug(f"Move_app:Exit-run")
         self.exit_server(process)
         exit()
      else:
         raise ValueError(f"Move_app:Unknown instruction: {instruction}")
      # Show the buffer
      self.matrixDisplay.showString(type)
      return type
      
    def isCriticalDistance(self):
        # Get the sensor readings in meters
        left_distance = self.robot.left_distance_sensor.distance
        right_distance = self.robot.right_distance_sensor.distance
        ##print("Left: {l:.2f}, Right: {r:.2f}".format(l=left_distance, r=right_distance))
        if left_distance < 0.2 or right_distance < 0.2:
            print("move_app:critical distance, Left: {0:.2f}, Right: {1:.2f}".format(
                  left_distance * 100, 
                  right_distance * 100))
            return True
        else:
            return False
        
    def getDistance(self):
        left_distance = self.robot.left_distance_sensor.distance
        right_distance = self.robot.right_distance_sensor.distance
        return left_distance, right_distance
        
    def getLogger(self):
        logger = logging.getLogger('move_application')
        logger.setLevel(logging.DEBUG)
        # create file handler which logs even debug messages
        fh = logging.FileHandler('log/move-app.log')
        fh.setLevel(logging.DEBUG)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)
        return logger
    
    def capture_array(self):
        return self.camera.capture_array()
    
    def make_display(self, display_frame):
        encoded_bytes = camera_stream.get_encoded_bytes_for_frame(display_frame)
        put_output_image(encoded_bytes)

    def process_frame(self, frame):
        (x, y, w, h) = self.find_object(frame)
        cv2.rectangle(frame, (x, y), (x + w, y + w), [255, 0, 0])
        self.make_display(frame)
        return x, y, w, h

    def findCamera(self, frame):
       
        (x, y, w, h) = self.process_frame(frame)
       
        if h > self.min_size:
            pan_error = self.center_x - (x + (w / 2))
            pan_value = self.pan_pid.get_value(pan_error)
            self.robot.set_pan(int(pan_value))
            tilt_error = self.center_y - (y + (h /2))
            tilt_value = self.tilt_pid.get_value(tilt_error)
            self.robot.set_tilt(int(tilt_value))
            print(f"x: {x}, y: {y}, pan_error: {pan_error}, tilt_error: {tilt_error}, pan_value: {pan_value:.2f}, tilt_value: {tilt_value:.2f}")
            return True
        else:
            return False

    def sayText(self, text):
        try:
            # Create the data payload as a dictionary
            payload = {
                "utterance": text
            }

            # Send a POST request to the server with the JSON data
            print(f"Sending request to {URL}...")
            response = requests.post(URL, data=json.dumps(payload), headers=headers)

            # Check if the request was successful
            if response.status_code == 200:
                print("Success! The server received the request.")
                print("Server response:", response.json())
            else:
                print(f"Error! Status code: {response.status_code}")
                print("Server response:", response.text)

        except requests.exceptions.ConnectionError as e:
            print(f"Failed to connect to the server at {URL}.")
            print("Please ensure the voice server is running and accessible.")
            print(f"Error details: {e}")      
    
    def stopMotors(self):
        print("move_app-stopMotors")
        self.robot.stop_motors()

    def setTiltSteps(self, steps):
        self.robot.set_tilt_steps(steps)

    def setPanSteps(self, steps):
        self.robot.set_pan_steps(steps)

    def setPanAngle(self, angle):
        self.robot.set_pan(angle)

    def setMatrixString(self, text):
        self.matrixDisplay.showString(text)

    def set_led_red(self):
        self.robot.set_led_red()

    def set_led_blue(self):
        self.robot.set_led_blue()

    def set_led_green(self):
        self.robot.set_led_green()

    def set_led_orange(self):
        self.robot.set_led_orange()

    def set_led_pink(self):
        self.robot.set_led_pink()

    def set_led_yellow(self):
        self.robot.set_led_yellow()

    def set_led_purple(self):
        self.robot.set_led_purple()