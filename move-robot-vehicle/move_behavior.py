import time

from image_app_core import start_server_process, get_control_instruction, put_output_image
from move_app import Move_app
from move_encoder import DriveController
import traceback
from core_utils import CoreUtils

## import debugpy
## ps -fA | grep python
## sudo netstat --all --program | grep '5001'
## debugpy.listen(('0.0.0.0', 5678))

# The text you want the voice server to speak
HI_TEXT = "Hello albrecht, my name is K6"
IMAGE_TEXT = "Hello who are you?"
DT = 0.01
TIMEOUT_IN = 10

# The headers specify that you are sending JSON data
headers = {
    "Content-Type": "application/json"
}

class Move_behavior():
   def __init__(self):
      self.last_time = time.time()
      self.logger = CoreUtils.getLogger("Move_behavior")
      self.execute = True
      self.found = False
      self.distance = False
      self.forwardRun = False
      # start camera
      self.logger.debug("move behavior: try to setup camera")
      self.move_app = Move_app()
      # indicate init done
      self.move_app.set_led_blue()
      
      self.logger.debug("move behavior: exit init forward behavior")

   def process_control(self):
      instruction = get_control_instruction()
      type = "_"
      while instruction:
         # execute instruction
         type = self.move_app.handle_instruction(instruction, self.process)
         self.logger.debug("move behavior: instruction type=" + type)
         if (self.move_app.isCommand(type)):
            self.found = False
            self.last_time = time.time()
            self.logger.debug(f"move behavior: type {type}")
            # show type on matrix
            self.move_app.setMatrixString(type)
            self.execute = True
            if type == "F":
               self.forwardRun = True
         if (self.move_app.isStop(type)):
             self.forwardRun = False
             self.execute = False
         # execute instruction
         instruction = get_control_instruction()
      return type

   def process(self):
      self.process = start_server_process('move.html')
      self.logger.debug("move behavior: process move behavior started")
      self.move_app.sayText(HI_TEXT)
   
      time_pan = time.time()
  
      # Main loop
      while True:
         try:
            type = self.process_control()
            if (not type):
               #self.logger.debug(f"work loop: {type} -timeout: {time.time() - time_say} -found: {self.found} - forward: {self.forwardRun}")
            #else:
               # self.logger.debug(f"move behavior: work loop - idle - found: {self.found} -execute {self.execute}")
               self.execute = False
            self.move_app.set_led_blue()

            if (self.forwardRun == True):
               DriveController.run(self.move_app)
               self.forwardRun = False
            if (self.execute and time.time() > self.last_time + TIMEOUT_IN):
               self.move_app.set_led_yellow()
               self.logger.debug("move behavior:move timeout")
               self.move_app.stopMotors()
               self.execute = False
            if not self.found and (time.time() > (time_pan + 2)):
               time_pan = time.time()
           
            time.sleep(DT)
         except Exception:
            self.logger.debug(traceback.format_exc())
            self.logger.debug("move behavior:close all")
            self.move_app.stopMotors()

CoreUtils.getLogger("Move_behavior").debug("move behavior:Starting move Behavior")
behavior = Move_behavior()
behavior.process()