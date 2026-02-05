import time
from multiprocessing import Process, Queue
from robot_gpio import Robot
from flask import Flask, render_template, Response, request
from core_utils import CoreUtils
# import debugpy
# debugpy.listen(('0.0.0.0', 5678))

app = Flask(__name__)
logger = CoreUtils.getLogger('image_app_core')
control_queue = Queue()
display_queue = Queue(maxsize=2)
display_template = 'image_server.html'
logger.info("Image_app_core: Start image app core")


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = "no-cache, no-store, must-revalidate"
    return response

@app.route('/')
def index():
    logger.info("image_app_core: index")
    return render_template(display_template)

@app.route('/start')
def start():
    logger.info("image_app_core: start")
    return start_server_process('move.html')

def frame_generator():
    while True:
        time.sleep(0.05)
        encoded_bytes = display_queue.get()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + encoded_bytes + b'\r\n')

@app.route('/display')
def display():
    logger.info("image_app_core: display")
    return Response(frame_generator(),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control', methods=['POST'])
def control():
    logger.info("image_app_core: route")
    Robot.set_led_orange()
    control_queue.put(request.form)
    return Response('queued')

@app.route('/ping')  # New route for health checks
def ping():
    ##print("ping")
    return "pong"

def start_server_process(template_name):
    global display_template
    logger.info("image_app_core: start_server_process")
    display_template = template_name
    server = Process(target=app.run, kwargs={"host": "0.0.0.0", "port": 5001})
    server.start()
    logger.info(f"Process-PID: {server.pid}")
    
    return server

def put_output_image(encoded_bytes):
    """Queue an output image"""
    if display_queue.empty():
        display_queue.put(encoded_bytes)

def get_control_instruction():
    if control_queue.empty():
        return None
    else:
        return control_queue.get()
    
def clear_queue():
    while not control_queue.empty():
        control_queue.get()
