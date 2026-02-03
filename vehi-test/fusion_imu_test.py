import time
import math

# Assuming you have the ICM library installed
# from icm20948 import ICM20948

def run_fusion_test(controller):
    print("--- Sensor Fusion Dry Run ---")
    print("Instructions:")
    print("1. Hold the robot in your hand.")
    print("2. The script will 'lock' the current direction as Target.")
    print("3. Rotate the robot left/right and watch the Motor Adjustments.")
    print("-----------------------------")
    
    # Initialize heading
    controller.target_heading = controller.get_calibrated_heading()
    controller.current_heading = controller.target_heading
    controller.last_time = time.time()
    
    print(f"Target Heading Locked at: {controller.target_heading:.2f}°")
    
    try:
        while True:
            # 1. Update the Filtered Heading
            curr_h = controller.update_fused_heading()
            
            # 2. Calculate Error (-180 to 180)
            error = controller.target_heading - curr_h
            if error > 180: error -= 360
            if error < -180: error += 360
            
            # 3. Calculate simulated adjustment (P-term only for test)
            adjustment = controller.kp_gyro * error
            
            # 4. Output Status
            print(f"Heading: {curr_h:6.2f}° | Error: {error:6.2f}° | Adjust: {adjustment:6.1f}", end='\r')
            
            # Visual feedback of what the wheels would do:
            if error > 2:
                status = "<- Turning Right to compensate"
            elif error < -2:
                status = "-> Turning Left to compensate"
            else:
                status = "   Driving Straight          "
            
            # print(status, end='\r') # Uncomment to see direction logic
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nTest Stopped.")

# To run:
drive_ctrl = DriveController(move_app)
run_fusion_test(drive_ctrl)