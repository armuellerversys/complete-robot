import time
import math
from Raspi_MotorHAT import Raspi_MotorHAT
from matrix_display import MatrixDisplay
from core_utils import CoreUtils
from move_app import Move_app
from move_sensor import SensorRobotCar
from icm20948 import ICM20948


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
        self.imu = ICM20948()
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
        self.kp_gyro = 4.0 
        self.ki_gyro = 0.01
        self.kd_gyro = 0.1
        
        self.gyro_integral = 0
        self.prev_gyro_error = 0

        self.stop_vehicle = False

        self.logger.info("move encoder: exit init forward behavior")

    def get_calibrated_heading(self):
        """Reads Magnetometer and applies offsets for a true heading."""
        raw_mag = self.imu.read_magnetometer_data() 
        #raw_mag = [0, 0, 0] # Placeholder
        
        # Apply Calibration
        mx = (raw_mag[0] - self.mag_offsets[0]) * self.mag_scales[0]
        my = (raw_mag[1] - self.mag_offsets[1]) * self.mag_scales[1]
        
        heading = math.degrees(math.atan2(my, mx))
        return heading % 360
    
    def update_fused_heading(self):
        """Combines Gyro and Mag into one stable value."""
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        
        # Get Gyro rate (degrees per second)
        gyro_z = self.imu.read_accelerometer_gyro_data()[2]
        self.logger.info(f"accelerometer-gyro_z {gyro_z}")
        
        # Get absolute Mag heading
        mag_h = self.get_calibrated_heading()
        self.logger.info(f"magnetometer-mag_h {mag_h}")

        # Complementary Filter
        # We use 'angle_difference' to prevent the filter from breaking at the 360/0 flip
        delta_gyro = gyro_z * dt
        self.current_heading = self.alpha * (self.current_heading + delta_gyro) + \
                               (1 - self.alpha) * mag_h
        
        return self.current_heading

    # --- Motor Control Helpers ---
    def set_motor_speed(self, motor_type, direction, speed):
        """Sets the direction and speed of a given motor."""
        motor = self.left_motor
        if motor_type == "R":
            motor = self.right_motor
        elif motor_type == "L":
            motor = self.left_motor
        speed = max(50, min(MAX_SPEED, speed))
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
        self.set_motor_speed("L", FORWARD, speed)
        self.set_motor_speed("R", FORWARD, speed)
        self.logger.debug("move-encoder:reset")

    def abs_left_encoder(self):
       return abs(self.left_encoder.steps)
    
    def abs_right_encoder(self):
       return abs(self.right_encoder.steps) 
    
    # --- PID Control Logic (Migrated and uses 'self.' variables) ---
    def move_straight_gyro_assisted(self, speed_target, distance_target):
        """The main loop replacing the old encoder-only PID."""
        left_counts = self.abs_left_encoder()
        right_counts = self.abs_right_encoder()
        distance = (left_counts + right_counts) / 2

        if self.stop_vehicle: return False

        if distance < distance_target:

            current_error = left_counts - right_counts 
            p_term = KP * current_error
            self.integral_error += current_error * DT
            i_term = KI * self.integral_error
            derivative = (current_error - self.previous_error) / DT
            d_term = KD * derivative
            adjust_encoder = (p_term + i_term + d_term) / 30
            self.logger.debug(f"adjustment: {adjust_encoder:4.1f} | p_term: {p_term:4.1f} | i_term: {i_term:4.1f} | d_term: {d_term:4.1f}")

            # 1. Update Heading
            curr_h = self.update_fused_heading()
            self.logger.info(f"fused curr_h {curr_h}")
            # 2. Calculate Angular Error
            # How far are we from our locked target direction?
            error = self.target_heading - curr_h
            self.logger.info(f"Update fused  {error}")

            # Handle the 360-degree wrap-around error
            if error > 180: error -= 360
            if error < -180: error += 360

            # 3. Heading PID
            p_term = self.kp_gyro * error
            self.gyro_integral += error * DT
            d_term = self.kd_gyro * ((error - self.prev_gyro_error) / DT)
            
            adjust_imu = p_term + (self.ki_gyro * self.gyro_integral) + d_term
            self.logger.info(f"Speed adjustment imu  {adjust_imu}")
            # 4. Motor Output
            # If error is positive (veered left), adjustment increases R speed and decreases L speed
            adjustment = adjust_encoder + adjust_imu * 0.1
            self.logger.info(f"Speed adjustment  {adjustment}")
            left_speed = speed_target - adjustment
            right_speed = speed_target + adjustment

            self.set_motor_speed("L", FORWARD, int(left_speed))
            self.set_motor_speed("R", FORWARD, int(right_speed))

            self.prev_gyro_error = error
            
            # Check for obstacles and stop signals
            return self.sensorRobotCar.run_avoidance_check(speed_target)
        else:
            self.release_motors()
            return False
    
    def run_backward(self):
        self.logger.info("run backward")
        
        self.right_motor.setSpeed(ROTATE_SPEED)
        self.right_motor.run(Raspi_MotorHAT.BACKWARD)
        self.left_motor.setSpeed(ROTATE_SPEED)
        self.left_motor.run(Raspi_MotorHAT.BACKWARD)
        back_encoder_steps = self.right_encoder.steps
        self.logger.info(f"Running right motor {TURN_STEPS} steps...")
        while True:
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
            if ((self.right_encoder.steps - right_encoder_steps)  > target_steps):
                 break
        self.right_motor.run(Raspi_MotorHAT.RELEASE) 
    
    def rotate_right(self, target_steps):
        self.logger.debug("rotate_right")
       
        # test left motor
        self.left_motor.setSpeed(ROTATE_SPEED)
        self.left_motor.run(Raspi_MotorHAT.FORWARD)
        left_encoder_steps = self.left_encoder.steps
        self.logger.debug(f"Running left motor {target_steps} steps...")
        while True:
            if ((self.left_encoder.steps -  left_encoder_steps)  > target_steps):
                 break
        self.left_motor.run(Raspi_MotorHAT.RELEASE) 

    def isCriticalDistance(self):
        return self.move_app.isLeftDistance() or self.move_app.isRightDistance() or self.move_app.isMidDistance()

    @staticmethod
    def getInstance(behavior):
        return DriveController(behavior)
    
    def run(self):
        DT = 0.5
        SAY_TIME = 20
        try:
            self.logger.info(f"Move_encoder: Starting movement with speed: {self.move_app.forward_speed} distance: {self.move_app.forward_distance }")

            self.reset(self.move_app.forward_speed)
          
            # Access the control method through the instance
            finish = True
            time_say = time.time()
            # Lock current heading as the 'North' we want to follow
            self.target_heading = self.get_calibrated_heading()
            self.current_heading = self.target_heading
            while finish:
                self.matrixDisplay.showMagnetometerAngle()
                
                finish = self.move_straight_gyro_assisted(self.move_app.forward_speed, self.move_app.forward_distance)
                self.logger.info(f"Finish received: {finish}")
                if (time.time() > (time_say + SAY_TIME)):
                    time_say = time.time()
                    self.move_app.sayText(ACTIVE_TEXT)

                type = self.behavior.process_control()
                self.logger.info(f"Command received: {type}")
                if (self.move_app.isStop(type)):
                    self.logger.info("Program stop received.")
                    self.release_motors()
                    return False

                time.sleep(DT)

            self.move_app.stopMotors()
            return True
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
        finally:
            self.release_motors()
            self.logger.error("Program finished.")

    def stop_vehicle(self):
        self.stop_vehicle = True

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

       
