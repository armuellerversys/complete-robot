#!/usr/bin/env python3
import time
from Raspi_MotorHAT import Raspi_MotorHAT
from gpiozero import DistanceSensor

    # ==========================================================
    #   BEHAVIOR TREE LOGIC
    # ==========================================================
OBSTACLE_CM = 25
# ==========================================================
#   GPIO / SENSOR SETUP (Pi 5 compatible)
# ==========================================================
class MoveSensor:
    # HC-SR04 sensors (change pins if needed)
    left_sensor  = DistanceSensor(echo=17,  trigger=27,  max_distance=3)
    front_sensor = DistanceSensor(echo=22, trigger=23, max_distance=3)
    right_sensor = DistanceSensor(echo=5, trigger=6, max_distance=3)

    def __init__(self, moveApp):
        self.moveApp = moveApp
            # ==========================================================
        #   MOTOR SETUP
        # ==========================================================
        mh = Raspi_MotorHAT(addr=0x64)   # Default MotorHAT address

        self.left_motor = mh.getMotor(1)
        self.right_motor = mh.getMotor(2)

    def get_distance_cm(sensor):
        """Return distance in cm, rounded."""
        return round(sensor.distance * 100, 1)

    def motors_stop(self):
        self.left_motor.run(Raspi_MotorHAT.RELEASE)
        self.right_motor.run(Raspi_MotorHAT.RELEASE)

    def motors_forward(self, speed=140):
        self.left_motor.setSpeed(speed)
        self.right_motor.setSpeed(speed)
        self.left_motor.run(Raspi_MotorHAT.FORWARD)
        self.right_motor.run(Raspi_MotorHAT.FORWARD)

    def motors_backward(self, speed=140):
        self.left_motor.setSpeed(speed)
        self.right_motor.setSpeed(speed)
        self.left_motor.run(Raspi_MotorHAT.BACKWARD)
        self.right_motor.run(Raspi_MotorHAT.BACKWARD)

    def motors_turn_left(self, speed=140):
        self.left_motor.setSpeed(0)
        self.right_motor.setSpeed(speed)
        self.left_motor.run(Raspi_MotorHAT.RELEASE)
        self.right_motor.run(Raspi_MotorHAT.FORWARD)

    def motors_turn_right(self, speed=140):
        self.left_motor.setSpeed(speed)
        self.right_motor.setSpeed(0)
        self.left_motor.run(Raspi_MotorHAT.FORWARD)
        self.right_motor.run(Raspi_MotorHAT.RELEASE)

    def obstacle_ahead(self):
        dist = self.get_distance_cm(self, self.front_sensor)
        print(f"Front = {dist} cm")
        return dist < OBSTACLE_CM

    def free_left(self):
        dist = self.get_distance_cm(self, self.left_sensor)
        print(f"Left  = {dist} cm")
        return dist > OBSTACLE_CM

    def free_right(self):
        dist = self.get_distance_cm(self, self.right_sensor)
        print(f"Right = {dist} cm")
        return dist > OBSTACLE_CM

    def act_forward(self):
        self.motors_forward(150)

    def act_stop(self):
        self.motors_stop()

    def act_turn_left(self):
        print("Turning left…")
        self.motors_turn_left(150)
        time.sleep(0.5)
        self.motors_stop()

    def act_turn_right(self):
        print("Turning right…")
        self.motors_turn_right(150)
        time.sleep(0.5)
        self.motors_stop()


# ==========================================================
#   BEHAVIOR TREE FRAMEWORK
# ==========================================================
class NodeStatus:
    SUCCESS = 1
    FAILURE = 2
    RUNNING = 3

class Node:
    def tick(self):
        raise NotImplementedError()


class Sequence(Node):
    """Runs children until one fails."""
    def __init__(self, children):
        self.children = children
    
    def tick(self):
        for c in self.children:
            st = c.tick()
            if st != NodeStatus.SUCCESS:
                return st
        return NodeStatus.SUCCESS


class Selector(Node):
    """Runs children until one succeeds."""
    def __init__(self, children):
        self.children = children
    
    def tick(self):
        for c in self.children:
            st = c.tick()
            if st in (NodeStatus.SUCCESS, NodeStatus.RUNNING):
                return st
        return NodeStatus.FAILURE


class Condition(Node):
    """Checks a boolean function."""
    def __init__(self, fn):
        self.fn = fn
    
    def tick(self):
        return NodeStatus.SUCCESS if self.fn() else NodeStatus.FAILURE


class Action(Node):
    """Executes a function and returns SUCCESS."""
    def __init__(self, fn):
        self.fn = fn
    
    def tick(self):
        self.fn()
        return NodeStatus.SUCCESS

# ----------------------------------------------------------
#   Navigator Behavior Tree
# ----------------------------------------------------------
NavigatorTree = Selector([
    # 1. Obstacle avoidance sequence
    Sequence([
        Condition(obstacle_ahead),

        Selector([
            Sequence([Condition(free_left),  Action(act_turn_left)]),
            Sequence([Condition(free_right), Action(act_turn_right)]),
            Action(act_turn_left)  # fallback
        ])
    ]),

    # 2. Default behavior: drive forward
    Action(act_forward)
])


# ==========================================================
#   MAIN LOOP
# ==========================================================
try:
    print("Starting behavior-tree navigation on Raspberry Pi 5...")
    while True:
        NavigatorTree.tick()
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping robot.")
    motors_stop()
