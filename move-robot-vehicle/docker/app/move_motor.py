from Raspi_MotorHAT import Raspi_MotorHAT
import traceback
from core_utils import CoreUtils
import time

logger = CoreUtils.getLogger("Move_motor")

class Move_motor:

    def __init__(self):
        mh = Raspi_MotorHAT(addr=0x64)
        self.lm = mh.getMotor(1)
        self.rm = mh.getMotor(2)
        logger.info("Move_motor init")
      
    def getMotors(self):
        logger.info("Move_motor: het motors")
        return self.lm, self.rm
    
    def turn_off_motors(self):
        logger.info("release motors")
        self.lm.run(Raspi_MotorHAT.RELEASE)
        self.rm.run(Raspi_MotorHAT.RELEASE)

    def run_forward(self, speed):
        try:
            logger.debug(f"run_forward: {speed}")
            self.lm.setSpeed(speed)
            self.rm.setSpeed(speed)
            self.lm.run(Raspi_MotorHAT.FORWARD)
            self.rm.run(Raspi_MotorHAT.FORWARD)
        except Exception:
            logger.error(traceback.format_exc())

    def run_backward(self, speed):
        try:
            logger.debug(f"run_backward: {speed}")
            self.lm.setSpeed(speed)
            self.rm.setSpeed(speed)
            self.lm.run(Raspi_MotorHAT.BACKWARD)
            self.rm.run(Raspi_MotorHAT.BACKWARD)
        except Exception:
            logger.error(traceback.format_exc())

    def left_forward(self, speed):
        try:
            if speed >= 0:
                logger.debug(f"left_forward: {speed}")
                self.lm.setSpeed(speed)
                self.lm.run(Raspi_MotorHAT.FORWARD)
            else:
                logger.debug(f"left_backward: {speed}")
                self.lm.setSpeed(speed * -1)
                self.lm.run(Raspi_MotorHAT.BACKWARD)
        except Exception:
            logger.error(traceback.format_exc())

    def right_forward(self, speed):
        try:
            if speed >= 0:
                logger.debug(f"right_forward: {speed}")
                self.rm.setSpeed(speed)
                self.rm.run(Raspi_MotorHAT.FORWARD)
            else:
                logger.debug(f"right_backward: {speed}")
                self.rm.setSpeed(speed * -1)
                self.rm.run(Raspi_MotorHAT.BACKWARD)
        except Exception:
            logger.error(traceback.format_exc())

    def run_left(self, speed):
        try:
            logger.debug(f"run_left: {speed}")
            self.lm.setSpeed(speed)
            self.rm.setSpeed(speed)
            self.lm.run(Raspi_MotorHAT.BACKWARD)
            self.rm.run(Raspi_MotorHAT.FORWARD)
            time.sleep(600/1000)
            self.turn_off_motors()
        except Exception:
            logger.error(traceback.format_exc())
            
    def run_right(self, speed):
        try:
            logger.debug(f"run_right: {speed}")
            self.lm.setSpeed(speed)
            self.rm.setSpeed(speed)
            self.lm.run(Raspi_MotorHAT.FORWARD)
            self.rm.run(Raspi_MotorHAT.BACKWARD)
            time.sleep(600/1000)
            self.turn_off_motors()
        except Exception:
            logger.error(traceback.format_exc())