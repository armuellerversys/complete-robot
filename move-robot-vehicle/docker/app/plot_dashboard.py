import requests
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time

# Replace with your Raspberry Pi's IP address
ROBOT_URL = "http://192.168.1.XX:5000"

class RobotDashboard:
    def __init__(self):
        self.headings = []
        self.errors = []
        self.times = []
        self.start_time = time.time()

        # Setup Plot
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, sharex=True)
        self.line1, = self.ax1.plot([], [], 'r-', label="Heading (deg)")
        self.line2, = self.ax2.plot([], [], 'b-', label="PID Error")
        
    def send_command(self, cmd):
        try:
            requests.post(f"{ROBOT_URL}/command", json={"action": cmd})
            print(f"Sent: {cmd}")
        except Exception as e:
            print(f"Connection Error: {e}")

    def update_plot(self, frame):
        try:
            # Request telemetry from your robot
            response = requests.get(f"{ROBOT_URL}/telemetry", timeout=0.1)
            data = response.json()
            
            self.times.append(time.time() - self.start_time)
            self.headings.append(data['heading'])
            self.errors.append(data['error'])
            
            # Keep only last 100 points
            self.times = self.times[-100:]
            self.headings = self.headings[-100:]
            self.errors = self.errors[-100:]

            self.line1.set_data(self.times, self.headings)
            self.line2.set_data(self.times, self.errors)
            
            self.ax1.relim(); self.ax1.autoscale_view()
            self.ax2.relim(); self.ax2.autoscale_view()
        except:
            pass
        return self.line1, self.line2

# Usage
dash = RobotDashboard()
# ani = FuncAnimation(dash.fig, dash.update_plot, interval=100)
# plt.show()