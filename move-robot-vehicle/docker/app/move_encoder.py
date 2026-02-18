import time
import math
from Raspi_MotorHAT import Raspi_MotorHAT
from matrix_display import MatrixDisplay
from core_utils import CoreUtils, RobotStopException
from move_app import Move_app
from move_sensor import SensorRobotCar
from robot_imu import RobotImu

# print("CWD:", os.getcwd())
# input('Hello! Start testing move_encoder:\n')

# --- Constants (Keep outside the class for easy modification) ---
FORWARD = Raspi_MotorHAT.FORWARD
RELEASE = Raspi_MotorHAT.RELEASE
DISTANCE_TEXT = "Caution critical distance"
ACTIVE_TEXT = "Caution I am running"
BASE_SPEED = 50
#KP = 0.5
KP = 0.7
KI = 0.005
KD = 0.05
#KD = 0.1
DT = 0.003

TURN_STEPS = 900
ROTATE_SPEED = 200
MAX_SPEED = 200
MIN_MOTOR_PWM = 60  # Minimum power to overcome gear friction

class DriveController:
    def __init__(self, behavior):

        self.logger = CoreUtils.getLogger("Move_encoder")
        self.logger.info("Initializing Drive Controller...")
        self.behavior = behavior
        self.move_app = behavior.move_app
        self.move_app.stopMotors()
        self.left_motor, self.right_motor = self.move_app.move_motor.getMotors()
        
        self.sensorRobotCar = SensorRobotCar(behavior, 150)
        # --- PID State Variables ---
        self.integral_error = 0
        self.previous_error = 0
       
        # Initialize the RotaryEncoder for the encoders
        # The Hall encoder generates pulses (counts) as the wheel turns.
        self.right_encoder = self.move_app.robot.right_encoder
        self.left_encoder = self.move_app.robot.left_encoder

        self.matrixDisplay = MatrixDisplay()
        
        # --- IMU Setup ---
        # Assuming you use a standard library for the ICM20948
        self.robot_imu = RobotImu()
        # 1. Calibration Data (Replace with results from your script)
        # OFFSETS: [-24.224999999999998, 36.224999999999994, 6.1499999999999995]
        # SCALES: [0.7663551401869159, 1.1549295774647887, 1.2058823529411764]
        self.mag_offsets = [-24.225, 36.225, 6.15] 
        self.mag_scales = [0.766, 1.155, 1.206]
        
        # 2. Filter & PID State
        self.alpha = 0.98            # Trust 98% Gyro, 2% Magnetometer
        self.current_heading = 0.0
        self.target_heading = 0.0
        self.last_time = time.time()
        
        # PID Gains (Start small, tune KP first)
        self.kp_gyro = 3.5 
        self.ki_gyro = 0.05
        self.kd_gyro = 0.15
        
        self.gyro_integral = 0
        self.prev_gyro_error = 0

        self.stop_flag= False
        self.logger.info(f"Target Heading:  {self.target_heading}")
        self.logger.info("move encoder: exit init forward behavior")

    def check_for_stop(self):
        """Centralized check for stop commands."""
        cmd_type = self.behavior.process_control()
        if self.move_app.isStop(cmd_type) or self.stop_flag:
            self.stop_flag = True
            self.logger.info("STOP command detected! Raising Exception.")
            raise RobotStopException("User requested stop")

    def get_calibrated_heading(self):
        """Reads Magnetometer and applies offsets for a true heading."""
        # raw_mag = self.imu.read_magnetometer_data() 
        raw_mag = self.robot_imu.read_magnetometer_data()
        #raw_mag = [0, 0, 0] # Placeholder
        
        # Apply Calibration
        mx = (raw_mag[0] - self.mag_offsets[0]) * self.mag_scales[0]
        my = (raw_mag[1] - self.mag_offsets[1]) * self.mag_scales[1]
        
        heading = math.degrees(math.atan2(my, mx))
        return heading % 360
    
    def update_fused_heading(self):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        
        # 1. Get raw inputs
        gyro_rate = self.get_gyro_rate()  # deg/s
        mag_heading = self.get_calibrated_heading() # 0-360
        
        # 2. Predict heading using Gyro
        predicted_heading = self.current_heading + (gyro_rate * dt)
        
        # 3. Calculate difference between Mag and Prediction (Wrap-aware)
        mag_error = self.calculate_heading_error(mag_heading, predicted_heading)
        
        # 4. Complementary Filter: 
        # Instead of Alpha * Gyro + (1-Alpha) * Mag, we "nudge" the prediction
        # toward the magnetometer by a small percentage of the error.
        self.current_heading = predicted_heading + (1 - self.alpha) * mag_error
        
        # 5. Keep final heading in 0-360 range
        self.current_heading %= 360
        
        return self.current_heading
    
    def get_mag_bearing(self):
        """Returns the absolute heading in degrees from the Magnetometer."""
        ## mag_x, mag_y, _ = self.imu.read_magnetometer_data()
        mag_x, mag_y, _ = self.robot_imu.read_magnetometer_data()
        bearing = math.degrees(math.atan2(mag_y, mag_x))
        return bearing

    def get_gyro_rate(self):
        """Returns the degrees per second rotation on the Z-axis."""
        _, _, gyro_z = self.robot_imu.read_gyroscope_data()
        return gyro_z

    # --- Motor Control Helpers ---
    def set_motor_speed(self, motor_type, direction, speed):
        """Sets the direction and speed of a given motor."""
        motor = self.left_motor if motor_type == "L" else self.right_motor
    
        # dead-zone compensation: if speed > 0 but < MIN, bump it up
        if 0 < speed < MIN_MOTOR_PWM:
            speed = MIN_MOTOR_PWM
            
        speed = max(0, min(MAX_SPEED, speed))
        motor.setSpeed(speed)
        motor.run(direction)
        self.logger.debug(f"set {motor_type} - Speed: {speed} - direction: {direction}")

    def release_motors(self):
        """Stops and releases both motors."""
        self.left_motor.run(RELEASE)
        self.right_motor.run(RELEASE)

    def reset(self, speed):
        # Reset PID state and counts at the start
        self.integral_error = 0
        self.previous_error = 0
        self.left_encoder.steps = 0 
        self.right_encoder.steps = 0  
        self.target_heading = self.get_mag_bearing()
        self.stop_flag = False
        self.set_motor_speed("L", FORWARD, speed)
        self.set_motor_speed("R", FORWARD, speed)
        self.logger.debug("move-encoder:reset")

    def abs_left_encoder(self):
       return abs(self.left_encoder.steps)
    
    def abs_right_encoder(self):
       return abs(self.right_encoder.steps) 
    
    def calculate_heading_error(self, target, current):
        """
        Calculates the shortest distance between two angles.
        Result is between -180 and +180.
        """
        error = target - current
        
        # If error is > 180, it's shorter to turn the other way
        while error > 180:
            error -= 360
        while error < -180:
            error += 360
            
        return error

    # --- PID Control Logic (Migrated and uses 'self.' variables) ---
    def move_straight_gyro_assisted(self, speed_target, distance_target):
        self.logger.info("move straight gyro assisted")
        # Call this at the very top of your loop
        self.check_for_stop()

        # 1. Calculate Distance & Check Completion
        left_counts = self.abs_left_encoder()
        right_counts = self.abs_right_encoder()
        distance = (left_counts + right_counts) / 2
        
        if distance >= distance_target or self.stop_flag:
            self.logger.info(f"move straight distance target reached {distance_target}")
            self.release_motors()
            return False

        # 2. Timing for the Filter
        now = time.time()
        dt = now - self.last_time
        if dt < 0.001: dt = 0.001 # Prevent division by zero
        self.last_time = now

        # 3. Get Fused Heading
        curr_h = self.update_fused_heading() # This now uses the wrap-aware logic
        
        # 4. Calculate Errors
        # Encoder Error (Speed sync)
        encoder_error = left_counts - right_counts 
        
        # IMU Error (Heading sync)
        imu_error = self.calculate_heading_error(self.target_heading, curr_h)

        # 5. Combined PID Logic
        # We apply a 'Weight' to each. Usually, IMU is more trusted for 'Straight'
        # than just matching encoder clicks.
        
        # Encoder Contribution
        adj_enc = (KP * encoder_error) + (KI * self.integral_error) 
        self.integral_error += encoder_error * dt
        
        # IMU Contribution (Stronger KP)
        adj_imu = (self.kp_gyro * imu_error) + (self.kd_gyro * (imu_error - self.prev_gyro_error) / dt)
        self.prev_gyro_error = imu_error

        # Total Adjustment
        # Note: We scale the IMU adjustment to match the motor speed scale (0-255)
        total_adjustment = (adj_enc * 0.4) + (adj_imu * 1.2)

        # 6. Motor Output with Safeguards
        left_speed = int(speed_target - total_adjustment)
        right_speed = int(speed_target + total_adjustment)
        
        self.set_motor_speed("L", FORWARD, left_speed)
        self.set_motor_speed("R", FORWARD, right_speed)

        # 7. Safety Check (Ultrasonic)
        # If an obstacle is detected, run_avoidance_check will handle reversing/turning.
        # We MUST re-lock the heading after avoidance finishes.
        if self.sensorRobotCar.isCriticalDistance():
            self.logger.info("Obstacle! Diverting to Avoidance Mode...")
            self.stop_flag = self.sensorRobotCar.run_avoidance_check(speed_target)
            # Re-check after avoidance finishes
            self.check_for_stop()
            # CRITICAL: Re-lock heading to whatever direction we are facing now
            # otherwise the robot will attempt a violent turn to its old heading.
            self.target_heading = self.get_calibrated_heading()
            self.current_heading = self.target_heading
            self.left_encoder.steps = 0 # Optional: Reset distance after avoidance
            self.right_encoder.steps = 0

        return True
    
    def run_backward(self):
        self.logger.info("run backward")
        
        self.right_motor.setSpeed(ROTATE_SPEED)
        self.right_motor.run(Raspi_MotorHAT.BACKWARD)
        self.left_motor.setSpeed(ROTATE_SPEED)
        self.left_motor.run(Raspi_MotorHAT.BACKWARD)
        back_encoder_steps = self.right_encoder.steps
        self.logger.info(f"Running right motor {TURN_STEPS} steps...")
        while True:
            time.sleep(0.001)
            if ((self.right_encoder.steps - back_encoder_steps)  > TURN_STEPS):
                 break
        self.right_motor.run(Raspi_MotorHAT.RELEASE) 

    def rotate_left(self, target_steps):
        self.logger.info("rotate_left")
    
        # rotate right motor
        self.right_motor.setSpeed(ROTATE_SPEED)
        self.right_motor.run(Raspi_MotorHAT.FORWARD)
        right_encoder_steps = self.right_encoder.steps
        self.logger.info(f"Running right motor {target_steps} steps...")
        while True:
            time.sleep(0.001)
            if ((self.right_encoder.steps - right_encoder_steps)  > target_steps):
                 break
        self.right_motor.run(Raspi_MotorHAT.RELEASE) 
    
    def rotate_right(self, target_steps):
        self.logger.info("rotate_right")
       
        # test left motor
        self.left_motor.setSpeed(ROTATE_SPEED)
        self.left_motor.run(Raspi_MotorHAT.FORWARD)
        left_encoder_steps = self.left_encoder.steps
        self.logger.info(f"Running left motor {target_steps} steps...")
        while True:
            time.sleep(0.001)
            if ((self.left_encoder.steps -  left_encoder_steps)  > target_steps):
                 break
        self.left_motor.run(Raspi_MotorHAT.RELEASE) 

    def isCriticalDistance(self):
        return self.move_app.isLeftDistance() or self.move_app.isRightDistance() or self.move_app.isMidDistance()
    
    def show_text(self, text):
        self.matrixDisplay.showString(text)

    @staticmethod
    def getInstance(behavior):
        return DriveController(behavior)

    
    def run(self):
        LOOP_DELAY = 0.01 
        display_update_time = time.time()
        
        try:
            self.reset(self.move_app.forward_speed)
            self.target_heading = self.get_calibrated_heading()
            self.current_heading = self.target_heading
            
            while not self.stop_flag:
                # 1. Logic Execution
                finish = self.move_straight_gyro_assisted(
                    self.move_app.forward_speed, 
                    self.move_app.forward_distance
                )
                
                # 2. Matrix Display Update (Every 0.5 seconds to keep it readable)
                if time.time() - display_update_time > 0.5:
                    dist = (self.abs_left_encoder() + self.abs_right_encoder()) / 2
                    
                    # Check if we are currently in an avoidance state
                    status_str = "AVOID" if self.sensorRobotCar.isCriticalDistance() else "OK"
                    
                    self.matrixDisplay.update_telemetry(
                        heading=self.current_heading,
                        distance=dist,
                        status=status_str
                    )
                    display_update_time = time.time()

                if not finish:
                    break
                    
                time.sleep(LOOP_DELAY)
        except RobotStopException:
            self.logger.info("Behavior interrupted by HTTP Stop Request.")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        finally:
            self.show_text("STOP")
            self.release_motors()
            self.logger.info("Motors released, returning to main program.")
            return # Returns control to the move_behavior / main app

    def stop_vehicle(self):
        self.stop_flag = True

## ▶️ Main Execution
if __name__ == '__main__':
    move_app = Move_app()
    try:
        input('Hello! Start testing move_encoder:\n')
        # Create the controller instance
        move_app.forward_speed = 100
        DriveController.run(move_app)
    except KeyboardInterrupt:
        print("Bye")
        move_app.stopMotors()

       
