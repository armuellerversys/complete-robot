from Raspi_MotorHAT import Raspi_MotorHAT
from robot_gpio import Robot
from time import sleep
import atexit
import traceback
from core_utils import CoreUtils

logger = CoreUtils.getLogger("control_server")
mh = Raspi_MotorHAT(addr=0x64)
lm = mh.getMotor(1)
rm = mh.getMotor(2)

def turn_off_motors():
  lm.run(Raspi_MotorHAT.RELEASE)
  rm.run(Raspi_MotorHAT.RELEASE)

atexit.register(turn_off_motors)
try:
  logger.info("test motors")

  Robot.set_led_orange()
 
  lm.setSpeed(100)
  rm.setSpeed(100)

  lm.run(Raspi_MotorHAT.FORWARD)
  rm.run(Raspi_MotorHAT.FORWARD)
  sleep(1)
except Exception:
  logger.info(traceback.format_exc())
  logger.info("close all")
finally:
  turn_off_motors()