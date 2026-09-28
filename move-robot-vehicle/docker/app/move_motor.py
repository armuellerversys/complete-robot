from Raspi_MotorHAT import Raspi_MotorHAT
import traceback
from core_utils import CoreUtils
import time

logger = CoreUtils.getLogger("Move_motor")

class Move_motor:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            # Create the object only if it doesn't exist
            cls._instance = super(Move_motor, cls).__new__(cls)
            # Flag to ensure __init__ only runs once
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Prevent re-initialization if Robot() is called again
        if self._initialized:
            return
        
        mh = Raspi_MotorHAT(addr=0x64)
        self.lm = mh.getMotor(1)
        self.rm = mh.getMotor(2)
        logger.info("Move_motor init")
      
    def getMotors(self):
        # logger.info("Move_motor: get motors")
        return self.lm, self.rm
    
    def turn_off_motors(self):
        logger.info("release motors")
        self.lm.run(Raspi_MotorHAT.RELEASE)
        self.rm.run(Raspi_MotorHAT.RELEASE)

    def run_joystick(self, left_speed, right_speed):
        try:
            logger.debug(f"run_joystick: left_speed={left_speed}, right_speed={right_speed}")
            if left_speed > 0:
                self.lm.run(Raspi_MotorHAT.FORWARD)
                self.lm.setSpeed(left_speed)
                self.rm.setSpeed(right_speed)
            else:
                self.lm.run(Raspi_MotorHAT.BACKWARD)
                self.lm.setSpeed(abs(left_speed))
                self.rm.setSpeed(abs(right_speed))
            if right_speed > 0:
                self.rm.run(Raspi_MotorHAT.FORWARD)
                self.lm.setSpeed(left_speed)
                self.rm.setSpeed(right_speed)
            else:
                self.rm.run(Raspi_MotorHAT.BACKWARD)
                self.lm.setSpeed(abs(left_speed))
                self.rm.setSpeed(abs(right_speed))
        except Exception:
            logger.error(traceback.format_exc())

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
        except Exception:
            logger.error(traceback.format_exc())

    def right_forward(self, speed):
        try:
            if speed >= 0:
                logger.debug(f"right_forward: {speed}")
                self.rm.setSpeed(speed)
                self.rm.run(Raspi_MotorHAT.FORWARD)
        except Exception:
            logger.error(traceback.format_exc())

    def left_backward(self, speed):
            try:
                if speed >= 0:
                    logger.debug(f"left_backward: {speed}")
                    self.lm.setSpeed(speed)
                    self.lm.run(Raspi_MotorHAT.BACKWARD)
            except Exception:
                logger.error(traceback.format_exc())
    
    def right_backward(self, speed):
            try:
                if speed >= 0:
                    logger.debug(f"right_backward: {speed}")
                    self.rm.setSpeed(speed)
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