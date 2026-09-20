import time

from robot_gpio import Robot
from move_motor import Move_motor
from image_app_core import clear_queue

class Vehi_app:

    def __init__(self, robot, move_motor, logger):
        self.robot = robot
        self.move_motor = move_motor
        self.logger = logger
        self.speed_right = 0
        self.speed_left = 0
        self.forward_speed = 0
        self.forward_distance = 0
        self.last_time = time.time()

    def handle_instruction(self, instruction, process):
      command = instruction['command']
      self.logger.info(f"Command: {command}")
      type = "-"
      if command == "set_left":
        type = "L"
        left_speed = int(instruction['speed'])
        self.move_motor.run_left(left_speed)
        self.robot.set_led_red()
        self.logger.info(f"Move_app:Left-speed: {left_speed:.2f}")
      elif command == "set_right":
        type = "R"
        right_speed = int(instruction['speed'])
        self.move_motor.run_right(right_speed)
        self.robot.set_led_red()
        self.logger.info(f"Move_app:Right-speed: {right_speed:.2f}")
      elif command == "set_backward":
         type = "B"
         backward_speed = int(instruction['speed'])
         self.move_motor.run_backward(backward_speed)
         self.robot.set_led_red()
         self.logger.info(f"Move_app:Backward-speed: {backward_speed:.2f}")
      elif command == "set_forward":
         type = "F"
         self.forward_speed = int(instruction['speed'])
         self.forward_distance = int(instruction['distance'])
         self.robot.set_led_red()
         self.logger.info(f"Move_app forward: speed: {self.forward_speed:.2f} | distance: {self.forward_distance:.2f}")
      elif command == "set_forward_left":
         type = "M"
         left_forward_speed = int(instruction['speed'])
         self.move_motor.left_forward(left_forward_speed)
         self.robot.set_led_red()
         self.logger.info(f"Move_app:forward_left-speed: {left_forward_speed:.2f}")
      elif command == "set_forward_right":
         type = "R"
         right_forward_speed = int(instruction['speed'])
         self.move_motor.right_forward(right_forward_speed)
         self.robot.set_led_red()
         self.logger.info(f"Move_app:forward_right-speed: {right_forward_speed:.2f}")
      elif command == "set_backward_left":
         type = "M"
         left_backward_speed = int(instruction['speed'])
         self.move_motor.left_backward(left_backward_speed)
         self.robot.set_led_red()
         self.logger.info(f"Move_app:backward_left-speed: {left_backward_speed:.2f}")
      elif command == "set_backward_right":
         type = "R"
         right_backward_speed = int(instruction['speed'])
         self.move_motor.right_backward(right_backward_speed)
         self.robot.set_led_red()
         self.logger.info(f"Move_app:backward_right-speed: {right_backward_speed:.2f}")
      elif command == "set_stop":
         print("stopping")
         type = "X"
         self.move_motor.turn_off_motors()
         clear_queue()
         self.robot.set_led_blue()
         self.logger.info("Move_app:Stop-run")
      elif command == "exit":
         print("Move_app:exiting")
         type = "-"
         self.move_motor.turn_off_motors()
         self.robot.set_led_blue()
         self.logger.info("Move_app:Exit-run")
         self.exit_server(process)
         exit()
      else:
        raise ValueError(f"Move_app:Unknown instruction: {instruction}")
      
      return type
