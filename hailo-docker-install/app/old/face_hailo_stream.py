#!/usr/bin/env python3
"""
Picamera2 + Hailo YOLOv8 person detection + LED Shim + MJPEG Flask Stream.

Person (class 0) -> LED lights RED.
Fallback to Haar cascade if HEF/Hailo not available.

Open on browser: http://<raspi-ip>:5000
"""

import os
import time
import threading
from typing import List, Tuple

import numpy as np
import cv2
from flask import Flask, Response, render_template_string

# -------- Picamera2 --------
from picamera2 import Picamera2

# -------- LED SHIM --------
try:
    import ledshim
    LEDSHIM_AVAILABLE = True
except:
    LEDSHIM_AVAILABLE = False

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


logger = HailoLogger.getLogger("Face-Hailo-ovos-Stream")
# -------- Hailo  --------
try:
    from hailo_platform import HEF, VDevice
    from hailo_platform.pyhailort import (
        InputVStream,
        OutputVStream,
        HailoSchedulingAlgorithm
    )
except:
    pass   # fallback will kick in

# -------- CONFIG ----------
HEF_PATH = "models/yolov8s_h8.hef"   # <-- set your actual path
USE_HAILO = os.path.exists(HEF_PATH)

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FLASK_PORT = 5000
LED_CLEAR_DELAY = 1.0
# --------------------------


# ===========================================================
# LED Shim
# ===========================================================
class LedShimController:
    def __init__(self):
        self.enabled = LEDSHIM_AVAILABLE
        if self.enabled:
            ledshim.set_clear_on_exit()
            # ledshim.setup()
            self.clear()

    def show_red(self):
        if not self.enabled:
            return
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, 255, 0, 0)
        ledshim.show()

    def show_green(self):
        if not self.enabled:
            return
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, 0, 255, 0)
        ledshim.show()

    def show_blue(self):
        if not self.enabled:
            return
        for i in range(ledshim.NUM_PIXELS):
            ledshim.set_pixel(i, 0, 0, 255)
        ledshim.show()

    def clear(self):
        if not self.enabled:
            return
        ledshim.clear()
        ledshim.show()

    def personLost(self):
        self.show_green()

led = LedShimController()


# ===========================================================
# Hailo Detector (w/ fallback)
# ===========================================================
class HailoDetector:
    def __init__(self, hef_path):
        self._use_hailo = False

        if hef_path and os.path.exists(hef_path):
            try:
                self.hef = HEF(hef_path)
                self.vdev = VDevice()
                self.network = self.vdev.configure(
                    self.hef,
                    scheduling_algorithm=HailoSchedulingAlgorithm.ROUND_ROBIN
                )

                in_info = self.hef.get_input_vstream_infos()[0]
                self.in_name = in_info.name
                self.in_h, self.in_w, _ = in_info.shape

                self.in_stream = InputVStream(self.in_name, self.vdev)
                self.out_streams = {
                    o.name: OutputVStream(o.name, self.vdev)
                    for o in self.hef.get_output_vstream_infos()
                }

                print("[Hailo] Using YOLOv8 HEF:", hef_path)
                self._use_hailo = True

            except Exception as e:
                print("[Hailo] Init failed:", e)

        if not self._use_hailo:
            print("[Detector] Using Haar fallback")
           
            xml = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.haar = cv2.CascadeClassifier(xml)

            self.in_w, self.in_h = 320, 320

    def _preprocess(self, frame):
        img = cv2.resize(frame, (self.in_w, self.in_h)).astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        return np.expand_dims(img, 0)

    def _postprocess(self, outputs, orig_shape):
        frame_h, frame_w = orig_shape[:2]

        out = next(iter(outputs.values()))
        out = np.array(out)

        if out.ndim == 3:
            out = out[0]

        boxes_xywh = out[:, 0:4]
        class_scores = out[:, 4:]
        scores = np.max(class_scores, axis=1)
        class_ids = np.argmax(class_scores, axis=1)

        mask = scores > 0.35
        boxes_xywh = boxes_xywh[mask]
        scores = scores[mask]
        class_ids = class_ids[mask]

        detections = []
        for (cx, cy, w, h), s, cid in zip(boxes_xywh, scores, class_ids):
            x1 = int((cx - w/2) / self.in_w * frame_w)
            y1 = int((cy - h/2) / self.in_h * frame_h)
            x2 = int((cx + w/2) / self.in_w * frame_w)
            y2 = int((cy + h/2) / self.in_h * frame_h)
            detections.append((x1, y1, x2, y2, float(s), int(cid)))

        return detections

    def infer(self, frame):
        if not self._use_hailo:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.haar.detectMultiScale(gray, 1.1, 4)
            return [(x, y, x+w, y+h, 0.9, 0) for x, y, w, h in faces]

        inp = self._preprocess(frame)
        self.in_stream.send(inp)
        outputs = {k: s.recv() for k, s in self.out_streams.items()}
        return self._postprocess(outputs, frame.shape)


detector = HailoDetector(HEF_PATH if USE_HAILO else None)

# ===========================================================
# Picamera2 Stream Thread
# ===========================================================
class PicamStream:
    def __init__(self):
        self.picam = Picamera2()
        config = self.picam.create_preview_configuration(
            main={"size": (FRAME_WIDTH, FRAME_HEIGHT),
                  "format": "RGB888"}
        )
        self.picam.configure(config)
        self.picam.start()

        self.frame = None
        self.dets = []
        self.running = True
        self.lock = threading.Lock()

        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self.running:
            frame = self.picam.capture_array()  # RGB888
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            dets = detector.infer(frame)

            with self.lock:
                self.frame = frame
                self.dets = dets

            time.sleep(0.01)

    def get(self):
        with self.lock:
            if self.frame is None:
                return None, []
            return self.frame.copy(), list(self.dets)


cam = PicamStream()


# ===========================================================
# Flask Stream
# ===========================================================
app = Flask(__name__)

HTML = """
<html>
<head><title>Picamera2 + Hailo Stream</title></head>
<body>
<h2>Picamera2 + Hailo (Person) Stream</h2>
<img src="{{ url_for('video_feed') }}" width="960">
</body>
</html>
"""


def draw(frame, dets):
    for x1, y1, x2, y2, sc, cid in dets:
        color = (0,255,0) if cid == 0 else (255,255,0)
        cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
        cv2.putText(frame, f"{cid}:{sc:.2f}", (x1, y1-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return frame


def mjpeg():
    last_led = 0
    last_person = False
    while True:
        frame, dets = cam.get()
        if frame is None:
            time.sleep(0.05)
            continue

        person = any(cid == 0 for *_, cid in dets)

        if person and not last_person:
            logger.info("\nPerson found")
            led.show_red()
            voice_controller.sayText("Hello Albrecht")
            last_led = time.time()
            last_person = person
        else:
            if time.time() - last_led > LED_CLEAR_DELAY:
                led.personLost()

        frame = draw(frame, dets)
        ok, jpg = cv2.imencode(".jpg", frame)
        if not ok:
            continue

        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
            jpg.tobytes() + b"\r\n"
        )


from ovos_pubsub import OvosPubSub
# ===========================================================
# OVOS Voice Controller
# ===========================================================
class VoiceController:
    def __init__(self, host="127.0.0.1", port=8181):
        self.speaker = OvosPubSub(host=host, port=port)
        # Subscribe to events
        self.last_say = time.time()
        self.logger = HailoLogger.getLogger("VoiceController")


    def sayText(self, text):
        """Method to call the OVOS speak API."""
        self.logger.info(f"[OVOS] Saying: {text}") # Add a log for confirmation
        if time.time() - self.last_say > 10:
            self.speaker.say(text)
            self.last_say = time.time()

# Initialize the instance globally
voice_controller = VoiceController()

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/video_feed")
def video_feed():
    return Response(mjpeg(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


# ===========================================================
# Main
# ===========================================================
if __name__ == "__main__":
    led.show_blue()
    try:
        app.run(host="0.0.0.0", port=FLASK_PORT, threaded=True)
    finally:
        cam.running = False
        led.clear()

