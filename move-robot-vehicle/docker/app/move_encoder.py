import time
from Raspi_MotorHAT import Raspi_MotorHAT
from image_app_core import get_control_instruction
from matrix_display import MatrixDisplay
from core_utils import CoreUtils
from move_app import Move_app
from move_sensor import SensorRobotCar
import debugpy
debugpy.listen(('0.0.0.0', 5678))

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
    def __init__(self, move_app):
        print("Initializing Drive Controller...")
        MOTOR_ADDR = 0x64
        LEFT_MOTOR_PORT = 1
        RIGHT_MOTOR_PORT = 2
        # --- Motor Setup ---
        self.mh = Raspi_MotorHAT(MOTOR_ADDR)
        self.left_motor = self.mh.getMotor(LEFT_MOTOR_PORT)
        self.right_motor = self.mh.getMotor(RIGHT_MOTOR_PORT)
        self.logger = CoreUtils.getLogger("Move_encoder")
        self.sensorRobotCar = SensorRobotCar(move_app, self.left_motor, self.right_motor, 150)
        # --- PID State Variables ---
        self.integral_error = 0
        self.previous_error = 0
        self.move_app = move_app
        # Initialize the RotaryEncoder for the encoders
        # The Hall encoder generates pulses (counts) as the wheel turns.
        self.right_encoder = move_app.robot.right_encoder
        self.left_encoder = move_app.robot.left_encoder

        self.matrixDisplay = MatrixDisplay()
        
        self.logger.debug("move encoder: exit init forward behavior")

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
    def move_straight_pid_control(self, speed_target, distance_target):

        left_counts = self.abs_left_encoder()
        right_counts = self.abs_right_encoder()
        distance = (left_counts + right_counts) / 2
        self.logger.debug(f"left_counts: {left_counts} |right_counts: {right_counts} | speed_target: {speed_target} | distance_target: {distance_target}")
        if distance < distance_target:
            current_error = left_counts - right_counts 

            p_term = KP * current_error

            self.integral_error += current_error * DT
            i_term = KI * self.integral_error
            
            derivative = (current_error - self.previous_error) / DT
            d_term = KD * derivative
            
            adjustment = (p_term + i_term + d_term) / 30

            self.logger.debug(f"adjustment: {adjustment:4.1f} | p_term: {p_term:4.1f} | i_term: {i_term:4.1f} | d_term: {d_term:4.1f}")

            left_speed = speed_target - adjustment
            right_speed = speed_target + adjustment

            self.set_motor_speed("L", FORWARD, int(left_speed))
            self.set_motor_speed("R", FORWARD, int(right_speed))

            self.previous_error = current_error

            self.logger.debug(f"L-counts: {left_counts} | R-counts: {right_counts} | E: {current_error} | LM: {left_speed:4.1f}  | RM: {right_speed:4.1f}")

            self.sensorRobotCar.run_avoidance_check(speed_target)
            
            if (self.move_app.is_stop_type(get_control_instruction())):
                self.logger.debug("move encoder stopped")
                self.release_motors()
                return False
            return True
        else:
            self.logger.debug("move encoder finish")
            self.release_motors()
            return False
    
    def run_backward(self):
        self.logger.debug("run backward")
        
        self.right_motor.setSpeed(ROTATE_SPEED)
        self.right_motor.run(Raspi_MotorHAT.BACKWARD)
        self.left_motor.setSpeed(ROTATE_SPEED)
        self.left_motor.run(Raspi_MotorHAT.BACKWARD)
        back_encoder_steps = self.right_encoder.steps
        self.logger.debug(f"Running right motor {TURN_STEPS} steps...")
        while True:
            if ((self.right_encoder.steps - back_encoder_steps)  > TURN_STEPS):
                 break
        self.right_motor.run(Raspi_MotorHAT.RELEASE) 


    def rotate_left(self, target_steps):
        self.logger.debug("rotate_left")
    
        # rotate right motor
        self.right_motor.setSpeed(ROTATE_SPEED)
        self.right_motor.run(Raspi_MotorHAT.FORWARD)
        right_encoder_steps = self.right_encoder.steps
        self.logger.debug(f"Running right motor {target_steps} steps...")
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

    ## run
    @staticmethod
    def run(moveApp):
        DT = 0.01
        SAY_TIME = 20
        robot_drive = DriveController(moveApp)
        try:
            robot_drive.reset(moveApp.forward_speed)
            robot_drive.logger.debug(f"Starting movement... {moveApp.forward_speed}")
            # Access the control method through the instance
            finish = True
            time_say = time.time()
            while finish:
                robot_drive.matrixDisplay.showMagnetometerAngle()
                ## move_straight_pid_control(self, speed_target, distance_target):
                finish = robot_drive.move_straight_pid_control(moveApp.forward_speed, 20000)
                if (time.time() > (time_say + SAY_TIME)):
                    time_say = time.time()
                    moveApp.sayText(ACTIVE_TEXT)

                time.sleep(DT)
            
        except Exception as e:
            robot_drive.logger.debug(f"An error occurred: {e}")
        finally:
            robot_drive.release_motors()
            robot_drive.logger.debug("Program finished.")


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

       
