import time
from Raspi_MotorHAT import Raspi_MotorHAT
from core_utils import CoreUtils, RobotStopException

COLLISION_DISTANCE_M = 20 # Collision Threshold in meters (25 cm)
TURN_STEPS = 600

class SensorRobotCar:
    """Class to encapsulate motor control and sensor reading for the vehicle."""
    
    def __init__(self, behavior, speed):
        self.logger = CoreUtils.getLogger("Move_sensor")
    
        self.behavior = behavior
        self.move_app = behavior.move_app

        self.motor_left, self.motor_right = self.move_app.move_motor.getMotors()
        self.speed = speed
        self.set_speed(speed)

        self.sensor_mid = self.move_app.sensor_mid
        self.sensor_left = self.move_app.sensor_left
        self.sensor_right = self.move_app.sensor_right

        self.right_encoder = self.move_app.robot.right_encoder
        self.left_encoder = self.move_app.robot.left_encoder

    def set_speed(self, speed):
        self.motor_left.setSpeed(speed)
        self.motor_right.setSpeed(speed)

    def forward(self):
        # print("Moving Forward")
        self.set_speed(self.speed)
        self.motor_left.run(Raspi_MotorHAT.FORWARD)
        self.motor_right.run(Raspi_MotorHAT.FORWARD)

    def stop(self):
        # print("Stopping")
        self.motor_left.run(Raspi_MotorHAT.RELEASE)
        self.motor_right.run(Raspi_MotorHAT.RELEASE)

    def reverse_slightly_timer(self):
        self.logger.debug("Reversing Slightly")
        self.motor_left.run(Raspi_MotorHAT.BACKWARD)
        self.motor_right.run(Raspi_MotorHAT.BACKWARD)
        time.sleep(0.5)
        self.stop()

    def reverse_by_encoder(self):
        self.logger.debug("run backward by encoder")
        
        right_back_encoder_steps = self.abs_right_encoder()
        left_back_encoder_steps = self.abs_left_encoder()
        self.logger.debug(f"Reverse backward state: {left_back_encoder_steps} -right: {right_back_encoder_steps}")
        self.motor_left.setSpeed(self.speed)
        self.motor_right.setSpeed(self.speed)
        self.motor_left.run(Raspi_MotorHAT.BACKWARD)
        self.motor_right.run(Raspi_MotorHAT.BACKWARD)
        
        self.logger.debug(f"Run backward {TURN_STEPS} steps...")
        left_ok = False
        right_ok = False
        while True:
            left_currentSteps = left_back_encoder_steps - self.abs_left_encoder() 
            right_currentSteps = right_back_encoder_steps - self.abs_right_encoder() 
            self.logger.debug(f"Reverse backward left-org: {left_back_encoder_steps} -right-org: {right_back_encoder_steps}")
            self.logger.debug(f"Reverse backward left: {left_currentSteps} -right: {right_currentSteps}")
            if (left_currentSteps > TURN_STEPS):
                self.motor_left.run(Raspi_MotorHAT.RELEASE)
                left_ok = True
            if (right_currentSteps > TURN_STEPS):
                self.motor_right.run(Raspi_MotorHAT.RELEASE)
                right_ok = True
            if left_ok and right_ok:
                self.stop()
                return True
            self.behavior.drive_controller.check_for_stop()
            time.sleep(0.1)

    def abs_left_encoder(self):
       left = abs(self.left_encoder.steps)
       self.logger.debug(f"Reverse backward left: {left}")
       return left
    
    def abs_right_encoder(self):
       right = abs(self.right_encoder.steps)
       self.logger.debug(f"Reverse backward right: {right}")
       return right
       
    def turn_gyro(self, angle_delta):
        """
        Rotates the robot by a specific number of degrees relative to current position.
        angle_delta: positive for right, negative for left.
        """
        # 1. Capture where we are starting from
        start_heading = self.behavior.drive_controller.get_calibrated_heading()
        target_heading = (start_heading + angle_delta) % 360
        
        self.logger.info(f"Turning from {start_heading:.1f} to {target_heading:.1f}")
        
        # 2. Set motors to rotate (Pivot)
        speed = 150 # Fixed rotation speed
        if angle_delta > 0: # Right
            self.motor_left.run(Raspi_MotorHAT.FORWARD)
            self.motor_right.run(Raspi_MotorHAT.BACKWARD)
        else: # Left
            self.motor_left.run(Raspi_MotorHAT.BACKWARD)
            self.motor_right.run(Raspi_MotorHAT.FORWARD)
        
        self.set_speed(speed)

        # 3. Monitor the turn
        while True:
            self.behavior.drive_controller.check_for_stop()

            current_h = self.behavior.drive_controller.get_calibrated_heading()
            # How much further do we have to go?
            error = self.behavior.drive_controller.calculate_heading_error(target_heading, current_h)
            
            # Stop if we are within 2 degrees of the target
            if abs(error) < 2.0:
                break
            
            time.sleep(0.01)

        self.stop()
        self.logger.info("Turn complete.")

    # Update the helper methods to use the new logic:
    def turn_left(self):
        self.turn_gyro(-90)

    def turn_right(self):
        self.turn_gyro(90)

    def get_distances_cm(self):
        """Returns distance readings in centimeters."""
        # DistanceSensor.distance property returns value in meters
        d_mid= abs(round(self.sensor_mid.distance * 100, 2))
        d_left = abs(round(self.sensor_left.distance * 100, 2))
        d_right = abs(round(self.sensor_right.distance * 100, 2))
        return d_mid, d_left, d_right

    def isCriticalDistance(self):
        d_mid, d_left, d_right = self.get_distances_cm()
        self.logger.debug(f"Distances (cm): F={d_mid}, L={d_left}, R={d_right}")
        return d_mid < COLLISION_DISTANCE_M or d_left < COLLISION_DISTANCE_M or d_right < COLLISION_DISTANCE_M
    
    def run_avoidance_check(self, speed):
        """The main collision avoidance logic, now interruptible."""
        try:
            if self.isCriticalDistance():
                self.logger.info("!!! Obstacle detected. Entering Avoidance Mode !!!")
                self.stop()
                
                # 1. Back up (Now checks for stop during the reverse loop)
                if not self.reverse_by_encoder():
                    return False # Stop received during reverse
                
                # Check stop again before turning
                self.behavior.drive_controller.check_for_stop()
                
                dist_mid, dist_left, dist_right = self.get_distances_cm()
                
                if dist_left > dist_right:
                    self.turn_left() # turn_gyro now includes check_for_stop
                else:
                    self.turn_right()
                
                return True 
            return False
        except RobotStopException:
            # Re-raise to be caught by the main run() loop
            raise

# --- Run the Program ---
if __name__ == '__main__':
    # !!! IMPORTANT: You must use a voltage divider on the HC-SR04 ECHO pin !!!
    # This protects your Raspberry Pi 5 GPIO pins from the sensor's 5V output.
    # 
    # Initialize and run the car
    
    MOTOR_LEFT_ID = 1  # Assuming left motor is connected to M1
    MOTOR_RIGHT_ID = 2 # Assuming right motor is connected to M2
    MOTOR_SPEED = 100  # Max speed is 255

    mh = Raspi_MotorHAT(addr=0x64)
    motor_left = mh.getMotor(MOTOR_LEFT_ID)
    motor_right = mh.getMotor(MOTOR_RIGHT_ID)
  
    try:
        input('Hello! Start testing move_encoder:\n')
        # Create the controller instance
       
        # move_behavior = Move_behavior()
        # move_behavior.move_app.forward_speed = 100
        sensor_car = SensorRobotCar(
            "move_behavior",
            speed=MOTOR_SPEED
        )
        sensor_car.set_speed(MOTOR_SPEED)
        sensor_car.forward()
        while True:
            time.sleep(0.001)
            sensor_car.run_avoidance_check(MOTOR_SPEED)
    except KeyboardInterrupt:
        print("Bye")
    finally:
         move_app.stopMotors()
