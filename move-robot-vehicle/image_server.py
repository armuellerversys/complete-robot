from flask import Flask, render_template, Response
import camera_stream
import time
import cv2

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('image_server.html')

def frame_generator():
    print("display image")
    """This is our main video feed"""
    camera = camera_stream.setup_camera()

    # allow the camera to warm up
    time.sleep(0.1)
 
    while True:
        frame = camera.capture_array()
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        print("stream len: " + str(len(frame_bytes)) + " time: " + str(time.time()))
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/display')
def display():
    return Response(frame_generator(),
        mimetype='multipart/x-mixed-replace; boundary=frame')


app.run(host="0.0.0.0", debug=True, port=5001)
