import time
import os, signal
from robot import Robot
import requests
import json
from matrix_display import MatrixDisplay
from image_app_core import put_output_image
from move_motor import Move_motor
from core_utils import CoreUtils
from image_app_core import clear_queue

# The URL of your Flask voice server
# Make sure to use the correct IP address and port
URL = "http://192.168.4.6:6000/say"

MINIMUM_DIST = 0.1
# The headers specify that you are sending JSON data
headers = {
    "Content-Type": "application/json"
}

class Move_app:
    def __init__(self):
        self.logger = CoreUtils.getLogger("Move_app")
        self.matrixDisplay = MatrixDisplay()
        # Set pan and tilt to middle, then clear it.
        self.robot = Robot()
        
        # warm up and servo move time
        time.sleep(0.1)
        self.move_motor = Move_motor()
        # set vertical angle

        self.speed_right = 0
        self.speed_left = 0
        self.forward_speed = 0
        self.forward_distance = 0
        self.last_time = time.time()
       
        self.sensor_front = self.robot.front_distance_sensor
        self.sensor_left = self.robot.left_distance_sensor
        self.sensor_right = self.robot.right_distance_sensor

        self.logger.debug("Move_app:Move-app init completed")         

    def exit_server(self, server):
        if server and server.is_alive():
            self.logger.debug(f"Move_app:Sending SIGINT to PID {server.pid}...")
            os.kill(server.pid, signal.SIGINT)  # graceful shutdown
            server.join(timeout=3)

            # Fallback in case SIGINT didn't work
            if server.is_alive():
                self.logger.debug("Move_app:SIGINT failed, force terminating...")
                server.terminate()
                server.join()
            self.matrixDisplay.showTemperatur()
            self.logger.debug("Server stopped cleanly.")
        else:
            self.logger.debug("Server not running.")

    def is_stop_type(self, instruction):
        if instruction is not None:
            command = instruction['command']
            self.logger.debug(f"Command: {command}")
            if command == "set_stop":
                return True
            if command == "exit":
                return True
        return False

    def handle_instruction(self, instruction, process):
      command = instruction['command']
      self.logger.debug(f"Command: {command}")
      type = "-"
      if command == "set_left":
        type = "L"
        left_speed = int(instruction['speed'])
        self.move_motor.run_left(left_speed)
        self.robot.set_led_red()
        self.logger.debug(f"Move_app:Left-speed: {left_speed:.2f}")
      elif command == "set_right":
        type = "R"
        right_speed = int(instruction['speed'])
        self.move_motor.run_right(right_speed)
        self.robot.set_led_red()
        self.logger.debug(f"Move_app:Right-speed: {right_speed:.2f}")
      elif command == "set_backward":
         type = "B"
         backward_speed = int(instruction['speed'])
         self.move_motor.run_backward(backward_speed)
         self.robot.set_led_red()
         self.logger.debug(f"Move_app:Backward-speed: {backward_speed:.2f}")
      elif command == "set_forward":
         type = "F"
         self.forward_speed = int(instruction['speed'])
         self.forward_distance = int(instruction['distance'])
         self.robot.set_led_red()
         self.logger.debug(f"Move_app forward: speed: {self.forward_speed:.2f} | distance: {self.forward_distance:.2f}")
      elif command == "set_forward_left":
         type = "M"
         left_forward_speed = int(instruction['speed'])
         self.move_motor.left_forward(left_forward_speed)
         self.robot.set_led_red()
         self.logger.debug(f"Move_app:forward_left-speed: {left_forward_speed:.2f}")
      elif command == "set_forward_right":
         type = "R"
         right_forward_speed = int(instruction['speed'])
         self.move_motor.right_forward(right_forward_speed)
         self.robot.set_led_red()
         self.logger.debug(f"Move_app:forward_right-speed: {right_forward_speed:.2f}")
      elif command == "set_stop":
         print("stopping")
         type = "X"
         self.move_motor.turn_off_motors()
         clear_queue()
         self.robot.set_led_blue()
         self.logger.debug("Move_app:Stop-run")
      elif command == "exit":
         print("Move_app:exiting")
         type = "-"
         self.move_motor.turn_off_motors()
         self.robot.set_led_blue()
         self.logger.debug("Move_app:Exit-run")
         self.exit_server(process)
         exit()
      else:
        raise ValueError(f"Move_app:Unknown instruction: {instruction}")
      
      return type
    
    def sayText(self, text):
        try:
            # Create the data payload as a dictionary
            payload = {"utterance": text}

            # Send a POST request to the server with the JSON data
            self.logger.debug(f"Sending request to {URL}...")
            response = requests.post(URL, data=json.dumps(payload), headers=headers)

            # Check if the request was successful
            if response.status_code == 200:
                self.logger.debug("Success! The voice server received the request.")
                self.logger.debug("Voice Server response:", response.json())
            else:
                self.logger.debug(f"Voice Server Error! Status code: {response.status_code}")
                self.logger.debug("Voice Server response:", response.text)

        except requests.exceptions.ConnectionError as e:
            self.logger.debug(f"Failed to connect to the Voice Server at {URL}.")
            self.logger.debug("Please ensure the voice Voice Server is running and accessible.")
            self.logger.debug(f"Error details: {e}")      
    
    def stopMotors(self):
        self.logger.debug("move_app-stopMotors")
        self.move_motor.turn_off_motors()

    def run_forward(self, speed):
        self.move_motor.run_forward(speed)

    def isCriticalDistance(self):
        # Get the sensor readings in meters
        left_distance = self.sensor_left.distance
        right_distance = self.sensor_right.distance
        front_distance = self.sensor_front.distance
        ##print("Left: {l:.2f}, Right: {r:.2f}".format(l=left_distance, r=right_distance))
        if left_distance < MINIMUM_DIST or right_distance < MINIMUM_DIST or front_distance < MINIMUM_DIST:
            self.logger.debug("move_app:critical distance, Left: {0:.2f} cm, Right: {1:.2f} cm, Mid: {1:.2f} cm".format(
                  left_distance * 100, right_distance * 100, front_distance * 100))
            return True
        else:
            return False
        
    def isLeftDistance(self):
        return abs(self.sensor_left.distance.distance) < MINIMUM_DIST
    
    def isRightDistance(self):
        return abs(self.sensor_right.distance.distance) < MINIMUM_DIST
    
    def isFrontDistance(self):
        return abs(self.robot.self.sensor_front.distance) < MINIMUM_DIST

    def isCommand(self, type):
        match type:
            case "F":
                return True
            case "R":
                return True
            case "L":
                return True
            case "B":
                return True
            case "M":
                return True
            case "R":
                return True
            case _:
                return False
            
    def isTurn(self, type):
        match type:
            case "L":
                return True
            case "B":
                return True
            case _:
                return False
            
    def isStop(self, type):
        match type:
            case "X":
                return True
            case _:
                return False

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

    def set_led_white(self):
        self.robot.set_led_white()