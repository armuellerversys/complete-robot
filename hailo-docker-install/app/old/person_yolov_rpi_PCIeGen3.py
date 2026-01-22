import cv2
import numpy as np
import time
import logging
import os
import ledshim
from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
import libcamera

# Hailo Platform Imports
from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams, 
                            ConfigureParams, InputVStreamParams, OutputVStreamParams, 
                            PcieDevice)
from hailo_platform.pyhailort.control_object import PcieHcpControl

# Environment setup for Hailo
os.environ['HAILO_MONITOR'] = '1'

# --- CONFIGURATION ---
HEF_PATH = 'yolov/yolov8m.hef'
LABELS = {0: 'person'} # Focused on person detection

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("PersonTracker_Gen3")

app = Flask(__name__)

# --- HTML TEMPLATE ---
HTML = '''
<html>
    <body style="background:#111; color:white; font-family:sans-serif; text-align:center;">
        <h1 style="margin-top:20px;">Hailo-8 PCIe Gen3 Monitor</h1>
        <div style="margin-bottom:10px;">
            <span style="color:#0f0;">● Live</span> | YOLOv8m Optimized
        </div>
        <img src="{{ url_for('video_feed') }}" style="border:5px solid #333; border-radius:10px; width:80%;">
    </body>
</html>
'''

# --- HARDWARE CONTROLLERS ---
class HardwareManager:
    def __init__(self):
        ledshim.set_clear_on_exit()
        self.clear_leds()
        
        # Initialize Camera
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(main={'format': 'BGR888', 'size': (640, 480)})
        self.picam2.configure(config)
        self.picam2.start()
        self.picam2.set_controls({"AwbMode": libcamera.controls.AwbModeEnum.Daylight})
        
        # Scan for Hailo Devices
        self.device_infos = PcieDevice.scan_devices()
        self.device_temps_t = [PcieHcpControl(device_info=di) for di in self.device_infos]

    def clear_leds(self):
        ledshim.clear()
        ledshim.show()

    def set_led_color(self, r, g, b):
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, r, g, b)
        ledshim.show()

    def get_hailo_temp(self):
        try:
            return self.device_temps_t[0].get_chip_temperature().ts0_temperature
        except:
            return 0.0

hw = HardwareManager()

# --- TRACKING & INFERENCE ---
class PersonTracker:
    def __init__(self):
        self.smooth_box = None
        self.alpha = 0.25         # Smoothing factor (Lower = smoother)
        self.persistence = 0      # Frames to keep box after loss
        self.prev_time = 0
        self.fps = 0

    def generate_frames(self):
        hef = HEF(HEF_PATH)
        
        with VDevice() as target:
            # 1. Hardware Configuration
            params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
            network_group = target.configure(hef, params)[0]
            input_params = InputVStreamParams.make_from_network_group(network_group)
            output_params = OutputVStreamParams.make_from_network_group(network_group)
            
            input_info = hef.get_input_vstream_infos()[0]
            h, w = input_info.shape[0], input_info.shape[1]
            
            # 2. Start Inference Pipeline
            with InferVStreams(network_group, input_params, output_params) as pipeline:
                with network_group.activate():
                    phys_dev = target.get_physical_devices()[0]
                    frame_count = 0
                    current_temp = hw.get_hailo_temp()
                    
                    while True:
                        frame = hw.picam2.capture_array()
                        if frame is None: break
                        
                        img_h, img_w = frame.shape[:2]
                        
                        # Calculate FPS
                        curr_time = time.time()
                        self.fps = 1 / (curr_time - self.prev_time) if self.prev_time > 0 else 0
                        self.prev_time = curr_time

                        # Run AI Inference every 2nd frame (Gen3 Optimization)
                        if frame_count % 2 == 0:
                            low_res = cv2.resize(frame, (w, h))
                            input_rgb = cv2.cvtColor(low_res, cv2.COLOR_BGR2RGB)
                            input_data = {input_info.name: np.expand_dims(input_rgb, axis=0)}
                            
                            results = pipeline.infer(input_data)
                            output_name = [k for k in results.keys() if 'nms' in k][0]
                            
                            # Parse Jagged NMS List
                            raw_results = results[output_name]
                            if isinstance(raw_results, list) and len(raw_results) > 0:
                                # Class 0 is Person
                                person_dets = np.array(raw_results[0][0]) 
                                
                                if person_dets.ndim == 2 and person_dets.shape[0] > 0:
                                    mask = person_dets[:, 4] > 0.50
                                    valid = person_dets[mask]
                                    
                                    if len(valid) > 0:
                                        # Box Smoothing Logic
                                        det = valid[0]
                                        new_box = np.array([det[1], det[0], det[3], det[2]]) # xmin, ymin, xmax, ymax
                                        
                                        if self.smooth_box is None:
                                            self.smooth_box = new_box
                                        else:
                                            self.smooth_box = (self.alpha * new_box) + ((1 - self.alpha) * self.smooth_box)
                                        
                                        self.persistence = 12 # Keep box for 12 frames
                                        hw.set_led_color(0, 255, 0) # Green
                                    else:
                                        self.handle_loss()
                                else:
                                    self.handle_loss()

                        # Update Temperature every 50 frames
                        if frame_count % 50 == 0:
                            current_temp = hw.get_hailo_temp()

                        # --- DRAW OVERLAYS ---
                        if self.smooth_box is not None:
                            x1, y1, x2, y2 = self.smooth_box
                            cv2.rectangle(frame, (int(x1*img_w), int(y1*img_h)), 
                                          (int(x2*img_w), int(y2*img_h)), (0, 255, 0), 2)
                            cv2.putText(frame, "PERSON", (int(x1*img_w), int(y1*img_h)-10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                        # Performance Dashboard
                        t_color = (0, 0, 255) if current_temp > 75 else (0, 255, 0)
                        cv2.putText(frame, f"FPS: {self.fps:.1f}", (20, 40), 0, 0.7, (255, 255, 0), 2)
                        cv2.putText(frame, f"TEMP: {current_temp:.1f}C", (frame.shape[1]-180, 40), 0, 0.7, t_color, 2)

                        frame_count += 1
                        _, buffer = cv2.imencode('.jpg', frame)
                        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    def handle_loss(self):
        if self.persistence > 0:
            self.persistence -= 1
        else:
            self.smooth_box = None
            hw.set_led_color(0, 0, 255) # Blue (Searching)

tracker = PersonTracker()

# --- FLASK ROUTES ---
@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/video_feed')
def video_feed():
    return Response(tracker.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    logger.info("Starting Web Server at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, threaded=True)
