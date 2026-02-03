import time
from Raspi_MotorHAT import Raspi_MotorHAT
from core_utils import CoreUtils
from move_app import Move_app
#import debugpy
#debugpy.listen(('0.0.0.0', 5678))
# --- Configuration Constants ---

COLLISION_DISTANCE_M = 20 # Collision Threshold in meters (25 cm)
TURN_STEPS = 600

class SensorRobotCar:
    """Class to encapsulate motor control and sensor reading for the vehicle."""
    
    def __init__(self, move_app, motor_left, motor_right, speed):
        self.logger = CoreUtils.getLogger("Move_sensor")
    
        self.left_motor , self.right_moto = self.move_app.move_motor.getMotors(self)
        self.speed = speed
        self.set_speed(speed)
        self.move_app = move_app
        
        self.sensor_front = move_app.sensor_front
        self.sensor_left = move_app.sensor_left
        self.sensor_right = move_app.sensor_right

        self.right_encoder = move_app.robot.right_encoder
        self.left_encoder = move_app.robot.left_encoder

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
                break
            time.sleep(0.1)

    def abs_left_encoder(self):
       left = abs(self.left_encoder.steps)
       self.logger.debug(f"Reverse backward left: {left}")
       return left
    
    def abs_right_encoder(self):
       right = abs(self.right_encoder.steps)
       self.logger.debug(f"Reverse backward right: {right}")
       return right
       
    def turn_left(self):
        # Time-based turn (replace with encoder logic for accuracy)
        self.logger.debug("Turning Left (Pivot)")
        self.motor_left.run(Raspi_MotorHAT.BACKWARD)
        self.motor_right.run(Raspi_MotorHAT.FORWARD)
        time.sleep(0.5)
        self.stop()

    def turn_right(self):
        # Time-based turn (replace with encoder logic for accuracy)
        self.logger.debug("Turning Right (Pivot)")
        self.motor_left.run(Raspi_MotorHAT.FORWARD)
        self.motor_right.run(Raspi_MotorHAT.BACKWARD)
        time.sleep(0.5)
        self.stop()

    def get_distances_cm(self):
        """Returns distance readings in centimeters."""
        # DistanceSensor.distance property returns value in meters
        d_front = abs(round(self.sensor_front.distance * 100, 2))
        d_left = abs(round(self.sensor_left.distance * 100, 2))
        d_right = abs(round(self.sensor_right.distance * 100, 2))
        return d_front, d_left, d_right

    def isCriticalDistance(self):
        d_front, d_left, d_right = self.get_distances_cm()
        self.logger.debug(f"Distances (cm): F={d_front}, L={d_left}, R={d_right}")
        return d_front < COLLISION_DISTANCE_M or d_left < COLLISION_DISTANCE_M or d_right < COLLISION_DISTANCE_M
    
    def run_avoidance_check(self, speed):
        """The main collision avoidance logic."""
        try:
            while self.isCriticalDistance():
                self.logger.debug("Starting collision avoidance loop")
                # Get distances (in cm)
                dist_front, dist_left, dist_right = self.get_distances_cm()
                
                # Check for collision in front
                if dist_front < COLLISION_DISTANCE_M:
                    self.logger.debug("!!! OBSTACLE DETECTED IN FRONT !!!")
                    self.stop()
                    self.reverse_by_encoder()
                    
                    # Decide turn direction based on clearest path
                    if dist_left > COLLISION_DISTANCE_M and dist_left >= dist_right:
                        self.logger.debug("Path clear on left, executing turn left.")
                        self.turn_left()
                    elif dist_right > COLLISION_DISTANCE_M:
                        self.logger.debug("Path clear on right, executing turn right.")
                        self.turn_right()
                    else:
                        # Fallback: Both sides blocked or left is slightly better but too close
                        self.logger.debug("Both sides restricted, executing default turn right.")
                        self.turn_right()
                elif dist_left < COLLISION_DISTANCE_M:
                    self.logger.debug("!!! OBSTACLE DETECTED on left side !!!")
                    self.stop()
                    self.reverse_by_encoder()
                    self.turn_right()
                elif dist_right < COLLISION_DISTANCE_M:
                    self.logger.debug("!!! OBSTACLE DETECTED on right side !!!")
                    self.stop()
                    self.reverse_by_encoder()
                    self.turn_left()
                # Normal Movement
                else:
                    self.logger.debug("!!! inconsisten  distance found!!!")
                    self.forward()
                
                # Small delay for loop stability
                time.sleep(0.1)
                self.forward()
        except KeyboardInterrupt:
            self.logger.debug("\nProgram stopped by user.")
            self.move_app.stopMotors()
    

# --- Run the Program ---
if __name__ == '__main__':
    # !!! IMPORTANT: You must use a voltage divider on the HC-SR04 ECHO pin !!!
    # This protects your Raspberry Pi 5 GPIO pins from the sensor's 5V output.
    # 
    # Initialize and run the car
    
    MOTOR_LEFT_ID = 1  # Assuming left motor is connected to M1
    MOTOR_RIGHT_ID = 2 # Assuming right motor is connected to M2
    MOTOR_SPEED = 100  # Max speed is 255

    mh = Raspi_MotorHAT(addr=MH_ADDR)
    motor_left = mh.getMotor(MOTOR_LEFT_ID)
    motor_right = mh.getMotor(MOTOR_RIGHT_ID)
    move_app = Move_app()
    try:
        input('Hello! Start testing move_encoder:\n')
        # Create the controller instance
        move_app.forward_speed = 100

        sensor_car = SensorRobotCar(
            move_app,
            motor_left,
            motor_right,
            speed=MOTOR_SPEED
        )
        sensor_car.set_speed(MOTOR_SPEED)
        sensor_car.forward()
        while True:
            sensor_car.run_avoidance_check(MOTOR_SPEED)
    except KeyboardInterrupt:
        print("Bye")
    finally:
         move_app.stopMotors()
