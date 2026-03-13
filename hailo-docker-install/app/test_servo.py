from Raspi_MotorHAT import Raspi_PWM_Servo_Driver

# --- Calibrated Values ---
HOME_PAN = 307 
HOME_TILT = 307

pwm = Raspi_PWM_Servo_Driver.PWM(0x42)
pwm.setPWMFreq(50)
pan_channel=0
tilt_channel=1

current_pan = HOME_PAN
current_tilt = HOME_TILT

def set_servo(channel, pulse):
    pulse = max(150, min(500, int(pulse)))
    pwm.setPWM(channel, 0, pulse)

def reset_position():
    current_pan = HOME_PAN
    current_tilt = HOME_TILT
    set_servo(pan_channel, current_pan)
    set_servo(tilt_channel, current_tilt)

reset_position() 
## max 200
offset = -240
print(f"Testing servo movement... {HOME_PAN + offset}")
set_servo(pan_channel, HOME_PAN + offset)