import time
from Raspi_MotorHAT import Raspi_PWM_Servo_Driver

class ServoController:
    def __init__(self, pan_channel=0, tilt_channel=1):
        self.pwm = Raspi_PWM_Servo_Driver.PWM(0x42)
        self.pwm.setPWMFreq(50)

        self.pan_channel = pan_channel
        self.tilt_channel = tilt_channel

        # --- Calibrated Values ---
        self.HOME_PAN = 307 
        self.HOME_TILT = 307
        
        # --- Limits (Prevent mechanical strain) ---
        self.MIN_PAN, self.MAX_PAN = 200, 550
        
        self.current_pan = self.HOME_PAN
        self.current_tilt = self.HOME_TILT
        
        # --- Scanning Config ---
        self.scan_step = 2        # How many units to move per frame
        self.scan_direction = 1   # 1 for Right, -1 for Left
        
        # --- Tracking Config ---
        self.DEADZONE = 70 
        self.SENSITIVITY = 0.04 

        self.reset_position()

    def set_servo(self, channel, pulse):
        pulse = max(150, min(600, int(pulse)))
        self.pwm.setPWM(channel, 0, pulse)

    def reset_position(self):
        self.current_pan = self.HOME_PAN
        self.current_tilt = self.HOME_TILT
        self.set_servo(self.pan_channel, self.current_pan)
        self.set_servo(self.tilt_channel, self.current_tilt)

    def scan(self):
        """Slowly sweeps the horizon searching for targets"""
        self.current_pan += (self.scan_step * self.scan_direction)
        
        # Reverse direction if limits hit
        if self.current_pan >= self.MAX_PAN:
            self.scan_direction = -1
        elif self.current_pan <= self.MIN_PAN:
            self.scan_direction = 1
            
        self.set_servo(self.pan_channel, self.current_pan)
        # Ensure tilt is at home during scan
        if abs(self.current_tilt - self.HOME_TILT) > 5:
            self.current_tilt = self.HOME_TILT
            self.set_servo(self.tilt_channel, self.current_tilt)

    def track_object(self, obj_center_x, obj_center_y, frame_w, frame_h):
        offset_x = obj_center_x - (frame_w // 2)
        offset_y = obj_center_y - (frame_h // 2)

        if abs(offset_x) > self.DEADZONE:
            self.current_pan -= (offset_x * self.SENSITIVITY)
            self.set_servo(self.pan_channel, self.current_pan)

        if abs(offset_y) > self.DEADZONE:
            self.current_tilt += (offset_y * self.SENSITIVITY)
            self.set_servo(self.tilt_channel, self.current_tilt)
