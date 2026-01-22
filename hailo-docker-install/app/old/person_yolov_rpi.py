import cv2
import numpy as np
import time
import logging
import os
import ledshim
from datetime import datetime # New import for timestamps
from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
import libcamera

# Hailo Platform Imports
from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams, 
                            ConfigureParams, InputVStreamParams, OutputVStreamParams, 
                            PcieDevice)
from hailo_platform.pyhailort.control_object import PcieHcpControl

# Environment setup
os.environ['HAILO_MONITOR'] = '1'
SNAPSHOT_DIR = "snapshots"
if not os.path.exists(SNAPSHOT_DIR):
    os.makedirs(SNAPSHOT_DIR)

# --- CONFIGURATION ---
HEF_PATH = 'yolov/yolov8m.hef'

class HailoLogger:
    @staticmethod
    def getLogger(name):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # CHECK if logger already has handlers before adding a new one
        if not logger.handlers: 
            # create console handler with a higher log level
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            
            # create formatter and add it to the handlers
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
            ch.setFormatter(formatter)
            
            # add the handler to the logger
            logger.addHandler(ch)
            
        return logger

logger = HailoLogger.getLogger("Face-Hailo-ovos-Stream")

app = Flask(__name__)

# --- HARDWARE & CAMERA ---
class HardwareManager:
    def __init__(self):
        ledshim.set_clear_on_exit()
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(main={'format': 'BGR888', 'size': (640, 480)})
        self.picam2.configure(config)
        self.picam2.start()
        self.device_infos = PcieDevice.scan_devices()
        self.device_temps_t = [PcieHcpControl(device_info=di) for di in self.device_infos]

    def set_led_color(self, r, g, b):
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, r, g, b)
        ledshim.show()

    def get_hailo_temp(self):
        try: return self.device_temps_t[0].get_chip_temperature().ts0_temperature
        except: return 0.0

hw = HardwareManager()

# --- TRACKING & SNAPSHOT LOGIC ---
class PersonTracker:
    def __init__(self):
        self.smooth_box = None
        self.alpha = 0.25
        self.persistence = 0
        self.fps = 0
        self.prev_time = 0
        self.last_snapshot_time = 0 
        self.snapshot_cooldown = 5  # Seconds between snapshots

    def save_snapshot(self, frame):
        """Saves current frame to disk with timestamp"""
        now = time.time()
        if now - self.last_snapshot_time > self.snapshot_cooldown:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(SNAPSHOT_DIR, f"person_{timestamp}.jpg")
            # Save the clean frame (or you can save 'frame' with the boxes)
            cv2.imwrite(filename, frame)
            logger.info(f"📸 Snapshot saved: {filename}")
            self.last_snapshot_time = now
            # Brief LED flash to indicate photo taken
            hw.set_led_color(255, 255, 255)

    def say_ovos(self, text):
        """Saves current frame to disk with timestamp"""
        now = time.time()
        if now - self.last_snapshot_time > self.snapshot_cooldown:
            voice_controller.sayText(text)
            logger.info(f"📸 OVOS saved: {text}")
            self.last_snapshot_time = now
            # Brief LED flash to indicate photo taken
            hw.set_led_color(255, 255, 255) 

    def generate_frames(self):
        hef = HEF(HEF_PATH)
        with VDevice() as target:
            params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
            network_group = target.configure(hef, params)[0]
            input_params = InputVStreamParams.make_from_network_group(network_group)
            output_params = OutputVStreamParams.make_from_network_group(network_group)
            input_info = hef.get_input_vstream_infos()[0]
            h, w = input_info.shape[0], input_info.shape[1]
            
            with InferVStreams(network_group, input_params, output_params) as pipeline:
                with network_group.activate():
                    frame_count = 0
                    current_temp = hw.get_hailo_temp()
                    
                    while True:
                        frame = hw.picam2.capture_array()
                        if frame is None: break
                        img_h, img_w = frame.shape[:2]
                        
                        # FPS calculation
                        curr_time = time.time()
                        self.fps = 1 / (curr_time - self.prev_time) if self.prev_time > 0 else 0
                        self.prev_time = curr_time

                        if frame_count % 2 == 0:
                            low_res = cv2.resize(frame, (w, h))
                            input_rgb = cv2.cvtColor(low_res, cv2.COLOR_BGR2RGB)
                            input_data = {input_info.name: np.expand_dims(input_rgb, axis=0)}
                            results = pipeline.infer(input_data)
                            
                            # Parse NMS
                            output_name = [k for k in results.keys() if 'nms' in k][0]
                            raw_results = results[output_name]
                            if isinstance(raw_results, list) and len(raw_results) > 0:
                                person_dets = np.array(raw_results[0][0]) 
                                
                                if person_dets.ndim == 2 and person_dets.shape[0] > 0:
                                    mask = person_dets[:, 4] > 0.55 # Slightly higher for snapshots
                                    valid = person_dets[mask]
                                    
                                    if len(valid) > 0:
                                        # Snapshot Logic
                                        self.say_ovos("Hello you")
                                        
                                        # Box Smoothing
                                        det = valid[0]
                                        new_box = np.array([det[1], det[0], det[3], det[2]])
                                        if self.smooth_box is None: self.smooth_box = new_box
                                        else: self.smooth_box = (self.alpha * new_box) + ((1 - self.alpha) * self.smooth_box)
                                        
                                        self.persistence = 10
                                        hw.set_led_color(0, 255, 0)
                                    else:
                                        self.handle_loss()
                                else:
                                    self.handle_loss()

                        if frame_count % 50 == 0:
                            current_temp = hw.get_hailo_temp()

                        # Draw box
                        if self.smooth_box is not None:
                            x1, y1, x2, y2 = self.smooth_box
                            cv2.rectangle(frame, (int(x1*img_w), int(y1*img_h)), (int(x2*img_w), int(y2*img_h)), (0, 255, 0), 2)

                        # HUD
                        t_color = (0, 0, 255) if current_temp > 75 else (0, 255, 0)
                        cv2.putText(frame, f"FPS: {self.fps:.1f} | Temp: {current_temp:.1f}C", (20, 40), 0, 0.7, t_color, 2)

                        frame_count += 1
                        _, buffer = cv2.imencode('.jpg', frame)
                        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    def handle_loss(self):
        if self.persistence > 0: self.persistence -= 1
        else:
            self.smooth_box = None
            hw.set_led_color(0, 0, 255)

tracker = PersonTracker()

from ovos_pubsub import OvosPubSub
# ===========================================================
# OVOS Voice Controller
# ===========================================================
class VoiceController:
    def __init__(self, host="127.0.0.1", port=8181):
        self.speaker = OvosPubSub(host=host, port=port)
        # Subscribe to events
        self.last_say = time.time()
        logger.info("VoiceController initialized") 

    def sayText(self, text):
        """Method to call the OVOS speak API."""
        logger.info(f"[VoiceController] Saying: {text}") # Add a log for confirmation
        if time.time() - self.last_say > 10:
            self.speaker.say(text)
            self.last_say = time.time()

# Initialize the instance globally
voice_controller = VoiceController()

@app.route('/')
def index():
    return render_template_string("<h1>Hailo-8 Live Feed</h1><img src='/video_feed' width='800'>")

@app.route('/video_feed')
def video_feed():
    return Response(tracker.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    voice_controller.sayText("Hello Albrecht")
    app.run(host='0.0.0.0', port=5000, threaded=True)
