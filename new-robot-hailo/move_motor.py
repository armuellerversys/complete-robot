from Raspi_MotorHAT import Raspi_MotorHAT
import traceback
from core_utils import CoreUtils
import time

mh = Raspi_MotorHAT(addr=0x64)
lm = mh.getMotor(1)
rm = mh.getMotor(2)
logger = CoreUtils.getLogger("Move_motor")

class Move_motor:
     
    def turn_off_motors(self):
        lm.setSpeed(0)
        rm.setSpeed(0)
        lm.run(Raspi_MotorHAT.FORWARD)
        rm.run(Raspi_MotorHAT.FORWARD)
    def run_forward(self, speed):
        try:
            logger.debug(f"run_forward: {speed}")
            lm.setSpeed(speed)
            rm.setSpeed(speed)
            lm.run(Raspi_MotorHAT.FORWARD)
            rm.run(Raspi_MotorHAT.FORWARD)
        except Exception:
            print(traceback.format_exc())
    def run_backward(self, speed):
        try:
            logger.debug(f"run_backward: {speed}")
            lm.setSpeed(speed)
            rm.setSpeed(speed)
            lm.run(Raspi_MotorHAT.BACKWARD)
            rm.run(Raspi_MotorHAT.BACKWARD)
        except Exception:
            print(traceback.format_exc())
    def left_forward(self, speed):
        try:
            if speed >= 0:
                logger.debug(f"left_forward: {speed}")
                lm.setSpeed(speed)
                lm.run(Raspi_MotorHAT.FORWARD)
            else:
                logger.debug(f"left_backward: {speed}")
                lm.setSpeed(speed * -1)
                lm.run(Raspi_MotorHAT.BACKWARD)
        except Exception:
            print(traceback.format_exc())
    def right_forward(self, speed):
        try:
            if speed >= 0:
                logger.debug(f"right_forward: {speed}")
                rm.setSpeed(speed)
                rm.run(Raspi_MotorHAT.FORWARD)
            else:
                logger.debug(f"right_backward: {speed}")
                rm.setSpeed(speed * -1)
                rm.run(Raspi_MotorHAT.BACKWARD)
        except Exception:
            print(traceback.format_exc())
    def run_left(self, speed):
        try:
            logger.debug(f"run_left: {speed}")
            lm.setSpeed(speed)
            rm.setSpeed(speed)
            lm.run(Raspi_MotorHAT.BACKWARD)
            rm.run(Raspi_MotorHAT.FORWARD)
            time.sleep(600/1000)
            self.turn_off_motors()
        except Exception:
            print(traceback.format_exc())
    def run_right(self, speed):
        try:
            logger.debug(f"run_right: {speed}")
            lm.setSpeed(speed)
            rm.setSpeed(speed)
            lm.run(Raspi_MotorHAT.FORWARD)
            rm.run(Raspi_MotorHAT.BACKWARD)
            time.sleep(600/1000)
            self.turn_off_motors()
        except Exception:
            print(traceback.format_exc())