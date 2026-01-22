import cv2
import numpy as np
import libcamera
from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
from hailo_platform import HEF, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams, InputVStreamParams, OutputVStreamParams, PcieDevice
from hailo_platform.pyhailort.control_object import PcieHcpControl
import ledshim
import os
# Must be set before importing hailo_platform
os.environ['HAILO_MONITOR'] = '1'

# import debugpy
# debugpy.listen(('0.0.0.0', 5678))

app = Flask(__name__)

# --- CONFIGURATION ---
HEF_PATH = 'yolov/yolov8m.hef'
# Standard COCO labels for YOLO
LABELS = {0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck', 15: 'cat', 16: 'dog'}
device_infos = PcieDevice.scan_devices()

HTML = ('''
        <html>
            <body style="background:#111; color:white; font-family:sans-serif; text-align:center;">
                <h1 style="margin-top:20px;">Hailo-8 person Monitor</h1>
                <img src="{{ url_for('video_feed') }}" style="border:5px solid #333; border-radius:10px;">
            </body>
        </html>
    ''')

# ===========================================================
# Logging setup
# ===========================================================
import logging

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


logger = HailoLogger.getLogger("person_yolov_rpi")

# ===========================================================
# LED Shim
# ===========================================================
class LedShimController:
    def __init__(self):
        ledshim.set_clear_on_exit()
        # ledshim.setup()
        self.clear()

    def show_red(self):
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, 255, 0, 0)
        ledshim.show()

    def show_green(self):
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, 0, 255, 0)
        ledshim.show()

    def show_blue(self):
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, 0, 0, 255)
        ledshim.show()

    def show_pink(self):
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, 255, 192, 203)
        ledshim.show()

    def show_yellow(self):
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, 255, 255, 0)
        ledshim.show()

    def show_orange(self):
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, 255, 165, 0)
        ledshim.show()

    def show_purple(self):
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, 160, 32, 240)
        ledshim.show()

    def clear(self):
        ledshim.clear()
        ledshim.show()

    def personLost(self):
        self.show_green()

logger.info("ledshim controller created")
led = LedShimController()
led.show_yellow()
picam2 = Picamera2()
led.show_pink()
config = picam2.create_preview_configuration(main={'format': 'BGR888', 'size': (640, 480)})
picam2.configure(config)
picam2.start()
picam2.set_controls({"AwbMode": libcamera.controls.AwbModeEnum.Daylight})
device_infos = PcieDevice.scan_devices()

device_infos = PcieDevice.scan_devices()
device_targets = [PcieDevice(device_info=di) for di in device_infos]
device_temps_t = [PcieHcpControl(device_info=di) for di in device_infos]

import time
import numpy as np
import cv2

class PersonTracker:
    def __init__(self):
        self.prev_time = 0
        self.fps = 0

    def getTemperatur(self, physical_device):
        try:
            # Direct hardware query via the control object
            temp_info = device_temps_t[0].get_chip_temperature()
            return temp_info.ts0_temperature
        except Exception as ex:
            logger.debug(f"Thermal read error: {ex}")
            return 0.0

    def generate_frames(self):
        hef = HEF(HEF_PATH)
        with VDevice() as target:
            configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
            network_group = target.configure(hef, configure_params)[0]
            input_params = InputVStreamParams.make_from_network_group(network_group)
            output_params = OutputVStreamParams.make_from_network_group(network_group)

            input_info = hef.get_input_vstream_infos()[0]
            h, w = input_info.shape[0], input_info.shape[1]
            
            with InferVStreams(network_group, input_params, output_params) as pipeline:
                phys_dev = target.get_physical_devices()[0]
                network_group.activate()
                with network_group.activate():
                    frame_count = 0
                    current_temp = self.getTemperatur(phys_dev)

                    while True:
                        frame = picam2.capture_array()
                        if frame is None: break

                        # --- FPS CALCULATION ---
                        curr_time = time.time()
                        self.fps = 1 / (curr_time - self.prev_time) if self.prev_time > 0 else 0
                        self.prev_time = curr_time

                        # --- FRAME SKIP LOGIC ---
                        # Only run AI every 2nd frame to keep video fluid at Gen 3 speeds
                        if frame_count % 2 == 0:
                            low_res = cv2.resize(frame, (w, h))
                            input_for_model = cv2.cvtColor(low_res, cv2.COLOR_BGR2RGB)
                            input_data = {input_info.name: np.expand_dims(input_for_model, axis=0)}
                            results = pipeline.infer(input_data)
                            
                            # 1. Get the raw list from the output layer
                            output_name = [k for k in results.keys() if 'nms' in k][0]
                            raw_results = results[output_name] 

                            # 2. Unwrap the nested structure
                            # Hailo NMS often returns [ [array_class0, array_class1, ...] ]
                            # We need to get inside that first outer list.
                            if isinstance(raw_results, list) and len(raw_results) > 0:
                                all_classes = raw_results[0]
                                
                                # 3. Get the Person Array (Class 0)
                                person_detections = all_classes[0]
                                
                                # 4. Now ensure it's a NumPy array for the [:, 4] slicing
                                person_detections = np.array(person_detections)

                                if person_detections.ndim == 2 and person_detections.shape[1] >= 5:
                                    # Now [:, 4] will work!
                                    mask = person_detections[:, 4] > 0.45
                                    valid_people = person_detections[mask]

                                    if len(valid_people) > 0:
                                        led.show_green()
                                        img_h, img_w = frame.shape[:2]
                                        for det in valid_people:
                                            ymin, xmin, ymax, xmax, score = det[:5]
                                            left, top = int(xmin * img_w), int(ymin * img_h)
                                            right, bottom = int(xmax * img_w), int(ymax * img_h)
                                            
                                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                                            cv2.putText(frame, f"Person {score:.2f}", (left, top - 10),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                                    else:
                                        led.show_blue()
                                

                        # --- DASHBOARD & OVERLAYS ---
                        if frame_count % 50 == 0:
                            current_temp = self.getTemperatur(phys_dev)

                        # Performance HUD
                        t_color = (0, 0, 255) if current_temp > 75 else (0, 255, 0)
                        cv2.putText(frame, f"FPS: {self.fps:.1f}", (20, 40), 0, 0.7, (255, 255, 0), 2)
                        cv2.putText(frame, f"Temp: {current_temp:.1f}C", (frame.shape[1]-170, 40), 0, 0.7, t_color, 2)

                        frame_count += 1
                        _, buffer = cv2.imencode('.jpg', frame)
                        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

led.show_pink()
personTracker = PersonTracker()  
logger.info("Person Tracker created")  

@app.route('/video_feed')
def video_feed():
    return Response(personTracker.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template_string(HTML)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)