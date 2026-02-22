
import time
from Raspi_MotorHAT import Raspi_MotorHAT
from core_utils import CoreUtils, RobotStopException
from move_app import Move_app
from matrix_display import MatrixDisplay
from move_encoder import DriveController
from move_behavior import Move_behavior

MAX_SPEED = 100

class TestDriveController:
    def __init__(self, behavior):
        self.logger = CoreUtils.getLogger("TestDriveController")
        self.move_app = Move_app()   
        self.left_motor, self.right_motor = self.move_app.move_motor.getMotors()
        self.matrixDisplay = MatrixDisplay()
        behavior = Move_behavior()
        behavior.move_app = self.move_app
        self.driverController = DriveController.getInstance(behavior)

        # PID parameters for heading lock test
        self.kp_gyro = 1.5
        self.ki_gyro = 0.01
        self.kd_gyro = 0.1
        self.prev_gyro_error = 0
        self.logger.info("--- test drive controller initialized ---")

    def test_heading_lock(self, duration=30):
        """
        Stays in place and fights to maintain the current heading.
        Good for testing if PID signs are correct.
        """
        self.logger.info("--- Heading Lock Active ---")

        self.target_heading = self.driverController.get_calibrated_heading()
        self.gyro_integral = 0
        start_time = time.time()

        try:
            while (time.time() - start_time) < duration:
                # 1. Get filtered heading
                curr_h = self.driverController.update_fused_heading()
                
                # 2. Calculate shortest-path error
                error = self.driverController.calculate_heading_error(self.target_heading, curr_h)
                
                # 3. PID logic (No base speed, speed_target = 0)
                p_term = self.kp_gyro * error
                self.gyro_integral = max(-100, min(100, self.gyro_integral + (error * 0.01)))
                derivative = (error - self.prev_gyro_error) / 0.01
                d_term = self.kd_gyro * derivative
                
                adjustment = p_term + (self.ki_gyro * self.gyro_integral) + d_term
                self.prev_gyro_error = error

                # 4. Apply to motors with 0 base speed
                # Note: We use a small base speed of 0, so the motors only move 
                # based on the PID adjustment.
                self.apply_pid_corrections(speed_target=0, adjustment=adjustment)
                
                # Show status on Matrix
                self.matrixDisplay.show_text(f"E{int(error)}")
                
                time.sleep(0.01)
                
        except RobotStopException:
            self.logger.info("Test stopped by user.")
        finally:
            self.release_motors()

    def apply_pid_corrections(self, speed_target, adjustment):
        """
        Refined logic that allows for both Forward travel and Pivot corrections.
        """
        # Calculate raw outputs
        left_raw = speed_target + adjustment
        right_raw = speed_target - adjustment

        # Determine direction for each motor based on the adjustment
        # This allows the robot to "Pivot" if speed_target is 0
        dir_l = Raspi_MotorHAT.FORWARD if left_raw >= 0 else Raspi_MotorHAT.BACKWARD
        dir_r = Raspi_MotorHAT.FORWARD if right_raw >= 0 else Raspi_MotorHAT.BACKWARD

        # Use absolute values for speed setting
        left_speed = max(0, min(MAX_SPEED, abs(left_raw)))
        right_speed = max(0, min(MAX_SPEED, abs(right_raw)))

        # Apply dead-zone (only if speed is actually required)
        MIN_PWM = 65 
        if 0 < left_speed < MIN_PWM: left_speed = MIN_PWM
        if 0 < right_speed < MIN_PWM: right_speed = MIN_PWM

        self.left_motor.setSpeed(int(left_speed))
        self.left_motor.run(dir_l)
        self.right_motor.setSpeed(int(right_speed))
        self.right_motor.run(dir_r)


## ▶️ Main Execution
if __name__ == '__main__':
    testDriveController = TestDriveController(None)
    testDriveController.test_heading_lock()