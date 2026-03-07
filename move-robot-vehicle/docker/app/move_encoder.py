import json
import queue
import time
import math
import requests
import threading
from Raspi_MotorHAT import Raspi_MotorHAT
from matrix_display import MatrixDisplay
from core_utils import CoreUtils, RobotStopException
from move_app import Move_app
from move_sensor import SensorRobotCar
from robot_imu import RobotImu
from matrix_text import Matrix

# --- Constants (Keep outside the class for easy modification) ---
FORWARD = Raspi_MotorHAT.FORWARD
RELEASE = Raspi_MotorHAT.RELEASE
DISTANCE_TEXT = "Caution critical distance"
ACTIVE_TEXT = "Caution I am running"
BASE_SPEED = 50
#KP = 0.5
KP = 0.7
KI = 0.005
KD = 0.1
#KD = 0.1
DT = 0.003

TURN_STEPS = 900
ROTATE_SPEED = 200
MAX_SPEED = 200
MIN_MOTOR_PWM = 60  # Minimum power to overcome gear friction

URL = "http://192.168.4.1:5000/showText"
# The headers specify that you are sending JSON data
headers = {
    "Content-Type": "application/json"
}

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

        self.error_start_time = time.time()
        self.stop_flag= False

        self.matrix = Matrix()
        self.matrixDisplay = MatrixDisplay()

        # New: Setup for background display updates
        self.display_queue = queue.Queue(maxsize=1) # Only keep the latest message
        self.display_thread = threading.Thread(target=self._display_worker, daemon=True)
        self.display_thread.start()

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
        self.show_text(f"H:{round(mag_heading)}")

        # Inside move_straight_gyro_assisted
        if abs(mag_heading - self.current_heading) > 45: # If we are off by more than 45 degrees
            if not hasattr(self, 'error_start_time'):
                self.error_start_time = time.time()
            elif time.time() - self.error_start_time > 2.0: # 2 seconds of huge error
                self.logger.error(f"Safety Trip: Continuous spinning detected. {abs(mag_heading)}")
                raise RobotStopException("Infinite spin detected")
        else:
            self.error_start_time = time.time() # Reset if error is small
        
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

    def reset_encoders(self):
        self.left_encoder.steps = 0 
        self.right_encoder.steps = 0  

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
        if error > 180: error -= 360
        if error < -180: error += 360
        return error

    def apply_pid_corrections(self, speed_target, adjustment):
        """
        Applies the PID adjustment to the motors with safety limits.
        adjustment: Positive means we need to turn Right (speed up Left).
        """
        # 1. Calculate raw speeds
        # If adjustment is +, left speeds up and right slows down -> turns Right
        left_raw = speed_target + adjustment
        right_raw = speed_target - adjustment

        # 2. Prevent "Spinning in Place" during straight travel
        # We want to ensure motors don't reverse unless specifically told to turn
        left_speed = max(0, min(MAX_SPEED, left_raw))
        right_speed = max(0, min(MAX_SPEED, right_raw))

        # 3. Handle the "Dead Zone" 
        # Gear motors won't move below a certain PWM (usually ~50-60)
        MIN_PWM = 60
        if 0 < left_speed < MIN_PWM: left_speed = MIN_PWM
        if 0 < right_speed < MIN_PWM: right_speed = MIN_PWM

        # 4. Final Execution
        self.set_motor_speed("L", FORWARD, int(left_speed))
        self.set_motor_speed("R", FORWARD, int(right_speed))
        
        self.logger.debug(f"Target: {speed_target} | Adj: {adjustment:.1f} | L: {int(left_speed)} R: {int(right_speed)}")


    # --- PID Control Logic (Migrated and uses 'self.' variables) ---
    def move_straight_gyro_assisted(self, speed_target, distance_target):
        self.logger.info("*********************** move straight gyro assisted ***********************")
        # Call this at the very top of your loop
        self.check_for_stop()

        # 1. Calculate Distance & Check Completion
        left_counts = self.abs_left_encoder()
        right_counts = self.abs_right_encoder()
        distance = (left_counts + right_counts) / 2
        self.logger.info(f"Encoder Left: {left_counts} Right: {right_counts} Distance: {distance:.1f} / {distance_target}")
        # 4. Calculate Errors
        # Encoder Error (Speed sync)
        encoder_error = right_counts - left_counts
        # Encoder Contribution
        now = time.time()
        dt = now - self.last_time
        adj_enc = (KP * encoder_error) + (KI * self.integral_error) 
        self.integral_error += encoder_error * dt
        if distance >= distance_target or self.stop_flag:
            self.logger.info(f"move straight distance target reached {distance_target}")
            self.release_motors()
            return False

        # 2. Timing for the Filter
       
        if dt < 0.001: dt = 0.001 # Prevent division by zero
        self.last_time = now

        # 3. Get Fused Heading
        curr_h = self.update_fused_heading() # This now uses the wrap-aware logic
        self.logger.info(f"Current Heading: {curr_h:.1f} Target Heading: {self.target_heading:.1f}")

        # IMU Error (Heading sync)
        imu_error = self.calculate_heading_error(self.target_heading, curr_h)

        # IMU Contribution (Stronger KP)
        # adj_imu = (self.kp_gyro * imu_error) + (self.kd_gyro * (imu_error - self.prev_gyro_error) / dt)
        # 2. PID Calculation
        p_term = self.kp_gyro * imu_error
        self.gyro_integral = max(-100, min(100, self.gyro_integral + (imu_error * dt))) # Anti-windup
        i_term = self.ki_gyro * self.gyro_integral
        d_term = self.kd_gyro * ((imu_error - self.prev_gyro_error) / dt)
        adj_imu = p_term + i_term + d_term
        self.logger.info(f"PID Terms => P: {p_term:.2f} I: {i_term:.2f} D: {d_term:.2f} | Total IMU Adj: {adj_imu:.2f}")

        self.prev_gyro_error = imu_error

        # Total Adjustment
        # Note: We scale the IMU adjustment to match the motor speed scale (0-255)
        total_adjustment = adj_enc - adj_imu
        self.logger.info(f"Total Adjustment: {total_adjustment:.1f} (Encoder Adj: {adj_enc:.1f}, IMU Adj: {adj_imu:.1f})")

        # 6. Motor Output with Safeguards
        self.apply_pid_corrections(speed_target, total_adjustment)

        # 7. Safety Check (Ultrasonic)
        # If an obstacle is detected, run_avoidance_check will handle reversing/turning.
        # We MUST re-lock the heading after avoidance finishes.
        if self.sensorRobotCar.isCriticalDistance():
            self.show_text("Dist Alert!")
            self.logger.info("Obstacle! Diverting to Avoidance Mode...")
            self.stop_flag = self.sensorRobotCar.run_avoidance_check(speed_target)
            # Re-check after avoidance finishes
            self.check_for_stop()
            # CRITICAL: Re-lock heading to whatever direction we are facing now
            # otherwise the robot will attempt a violent turn to its old heading.
            self.target_heading = self.get_calibrated_heading()
            self.current_heading = self.target_heading
            self.reset_encoders()
            self.logger.info(f"Post-Avoidance Heading Re-locked to: {self.target_heading:.1f}")
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
            self.behavior.drive_controller.check_for_stop()
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
        self.logger.info(f"Running left motor {target_steps} steps...")
        while True:
            self.behavior.drive_controller.check_for_stop()
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
        self.logger.info(f"Running right motor {target_steps} steps...")
        while True:
            self.behavior.drive_controller.check_for_stop()
            time.sleep(0.001)
            if ((self.left_encoder.steps -  left_encoder_steps)  > target_steps):
                 break
        self.left_motor.run(Raspi_MotorHAT.RELEASE) 

    def isCriticalDistance(self):
        return self.move_app.isLeftDistance() or self.move_app.isRightDistance() or self.move_app.isMidDistance()
    
    def _display_worker(self):
        """Background thread that handles slow network requests."""
        while True:
            try:
                # This blocks here until a message is put in the queue
                text = self.display_queue.get()
                self.logger.info("Display worker {text}")
                payload = {"message": text}
                # Increased timeout to 3 seconds so it doesn't crash easily
                response = requests.post(URL, json=payload, headers=headers, timeout=3)
                
                if response.status_code != 200:
                    self.logger.error(f"Matrix Error: {response.status_code}")
                
                # Tell the queue we are done
                self.display_queue.task_done()
            except requests.exceptions.RequestException:
                # We don't want the background thread to crash the whole program
                self.logger.warning("Matrix server unreachable or timed out.")
            except Exception as e:
                self.logger.error(f"Display worker error: {e}")
    
    
    def show_text(self, text):
        self.logger.info(f"Show text: {text}")
        self.matrix.show_text(text)
        ## self.matrixDisplay.showString(text)
        #curl -X POST http://192.168.4.1:5000/showText -H "Content-Type: application/json" \-d '{"message": "This is a test"}'
        #try:
         #   self.logger.info(f"Show text: {text}")
         #   # use block=False so the PID loop NEVER waits for the queue
         #   self.display_queue.put_nowait(text)
        #except queue.Full:
          #  # If the background thread is busy, skip this update to keep loop speed
          #  pass
        #except requests.exceptions.ConnectionError as e:
           # self.logger.error(f"Failed to connect to the Matrix Server at {URL}.")
           # self.logger.error(f"Error details: {e}")

    @staticmethod
    def getInstance(behavior):
        return DriveController(behavior)

    def run(self):
        LOOP_DELAY = 0.01 
        display_update_time = time.time()
        self.logger.info("Start encoder behavior")
        self.show_text("Start enc")
        try:
            self.reset(self.move_app.forward_speed)
            self.target_heading = self.get_calibrated_heading()
            self.current_heading = self.target_heading
            self.error_start_time = time.time() 
            
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

                    # Format a combined string of heading and distance
                    heading_str = f"H:{int(self.current_heading)}"
                    self.show_text(heading_str)

                    display_update_time = time.time()

                if not finish:
                    break
                    
                time.sleep(LOOP_DELAY)
        except RobotStopException:
            self.logger.info("Behavior interrupted by HTTP Stop Request.")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        finally:
            # self.show_text("STOP")
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
