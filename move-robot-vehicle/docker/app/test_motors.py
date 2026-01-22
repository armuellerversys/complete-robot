from Raspi_MotorHAT import Raspi_MotorHAT
from robot import Robot
from time import sleep
import atexit
import traceback

mh = Raspi_MotorHAT(addr=0x64)
lm = mh.getMotor(1)
rm = mh.getMotor(2)

def turn_off_motors():
  lm.run(Raspi_MotorHAT.RELEASE)
  rm.run(Raspi_MotorHAT.RELEASE)

atexit.register(turn_off_motors)
try:
  Robot.set_led_orange()
 
  lm.setSpeed(100)
  rm.setSpeed(100)

  lm.run(Raspi_MotorHAT.FORWARD)
  rm.run(Raspi_MotorHAT.FORWARD)
  sleep(1)
except Exception:
  print(traceback.format_exc())
  print("close all")
finally:
  turn_off_motors()