
from icm20948 import ICM20948
import time

def calibrate_magnetometer(imu_sensor):
    print("Starting Calibration... Rotate the robot 360 degrees slowly.")
    
    # Initialize min/max with extreme values
    mag_min = [999, 999, 999]
    mag_max = [-999, -999, -999]
    
    start_time = time.time()
    while time.time() - start_time < 30:  # Calibrate for 30 seconds
        # Replace with your actual library read command
        mag_data = imu_sensor.read_magnetometer_data() 
        
        for i in range(3):
            if mag_data[i] < mag_min[i]: mag_min[i] = mag_data[i]
            if mag_data[i] > mag_max[i]: mag_max[i] = mag_data[i]
            
        time.sleep(0.05)

    # Calculate Offsets (Hard Iron) and Scale (Soft Iron)
    offsets = [(mag_max[i] + mag_min[i]) / 2 for i in range(3)]
    
    # Calculate average radius to normalize the scale
    avg_delta = [(mag_max[i] - mag_min[i]) / 2 for i in range(3)]
    avg_radius = sum(avg_delta) / 3
    scales = [avg_radius / d if d != 0 else 1.0 for d in avg_delta]

    print(f"Calibration Complete!")
    print(f"OFFSETS: {offsets}")
    print(f"SCALES: {scales}")
    return offsets, scales
##
# OFFSETS: [-24.224999999999998, 36.224999999999994, 6.1499999999999995]
# SCALES: [0.7663551401869159, 1.1549295774647887, 1.2058823529411764]
print ("Start Calibration")
imu_sensor = ICM20948()
calibrate_magnetometer(imu_sensor)