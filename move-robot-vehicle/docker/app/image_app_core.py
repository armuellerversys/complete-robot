from multiprocessing import Process, Queue
import time
import debugpy
from flask import Flask, Response, render_template, request

from core_utils import CoreUtils
from robot_gpio import Robot

try:
    debugpy.listen(("0.0.0.0", 5678))
except Exception:
    pass

app = Flask(__name__)
logger = CoreUtils.getLogger("image_app_core")

control_queue = Queue()
display_queue = Queue(maxsize=2)
display_template = "image_server.html"

logger.info("image_app_core: Initialization complete")


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.route("/")
def index():
    logger.info("image_app_core: Route GET /")
    return render_template(display_template)


@app.route("/start")
def start():
    logger.info("image_app_core: Route GET /start")
    return start_server_process("move.html")


def frame_generator():
    while True:
        time.sleep(0.05)
        if not display_queue.empty():
            encoded_bytes = display_queue.get()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + encoded_bytes + b"\r\n"
            )


@app.route("/display")
def display():
    logger.info("image_app_core: Route GET /display")
    return Response(
        frame_generator(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/control", methods=["POST"])
def control():
    logger.info(f"image_app_core: Route POST /control data={request.form}")
    Robot.set_led_orange()
    control_queue.put(request.form.to_dict())
    return Response("queued", status=200)


@app.route("/ping")
def ping():
    return "pong", 200


@app.route("/telemetry", methods=["GET"])
def get_telemetry():
    # Placeholder telemetry response (integrate drive_controller instance when ready)
    return {
        "heading": 0.0,
        "target": 0.0,
        "error": 0.0,
        "distance": 0.0,
    }


def start_server_process(template_name: str) -> Process:
    global display_template
    logger.info("image_app_core: Launching server sub-process")
    display_template = template_name

    server = Process(
        target=app.run, kwargs={"host": "0.0.0.0", "port": 5001, "threaded": True}
    )
    server.start()
    logger.info(f"Server sub-process running (PID: {server.pid})")
    return server


def put_output_image(encoded_bytes: bytes):
    """Queues an output frame without blocking when full."""
    if display_queue.empty():
        display_queue.put(encoded_bytes)


def get_control_instruction():
    """Retrieves an instruction from the queue or returns None."""
    if control_queue.empty():
        return None
    return control_queue.get()

def put_control_instruction(instruction: dict):
    """Queues a control instruction without blocking when full."""
    if control_queue.empty():
        control_queue.put(instruction)

def clear_queue():
    while not control_queue.empty():
        try:
            control_queue.get_nowait()
        except Exception:
            break