from flask import Flask, render_template, render_template_string, jsonify, request
from robot_modes import RobotModes
from robot import Robot
from gpiozero import devices
from matrix_display import MatrixDisplay
import socket
import time
from core_utils import CoreUtils

## import debugpy
## debugpy.listen(('0.0.0.0', 5678))
## sudo shutdowndebugpy.wait_for_client()

# A Flask App contains all its routes.
app = Flask(__name__)

# Prepare our robot modes for use
mode_manager = RobotModes()

Robot.set_green_one()

print("Show matrix")
matrixDisplay = MatrixDisplay()
# stop_event = matrixDisplay.showClock()
matrixDisplay.showTemperatur()
logger = CoreUtils.getLogger("control_server")

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = "no-cache, no-store, must-revalidate"
    return response

@app.route("/")
def index():
    logger.debug("index")
    matrixDisplay.showTemperatur()
    return render_template('menu.html', menu=mode_manager.menu_config)

@app.route("/run/<mode_name>", methods=['POST'])
def run(mode_name):
    logger.debug("route run/" + mode_name)
    Robot.set_led_white()
 
    # Use our robot app to run something with this mode_name
    mode_manager.run(mode_name)
    response = {'message': f'{mode_name} running'}
    if mode_manager.should_redirect(mode_name):
        response['redirect'] = True
    else:
        response['redirect'] = False
        
    ret_response = jsonify(response)
    logger.debug(f"Response: {ret_response}")
    return ret_response

@app.route("/stop", methods=['POST'])
def stop():
    logger.debug("stop")
    devices._shutdown()
    time
    Robot.set_led_orange()
    matrixDisplay.showTemperatur()
    # Tell our system to stop the mode it's in.
    mode_manager.stop()
    logger.debug(f"Stop executed")
    return jsonify({'message': "Stopped"})

@app.route("/state", strict_slashes=False)
def state():
    logger.debug("state request received")
    Robot.set_led_orange()
    time.sleep(1)
    Robot.set_led_white()
    time.sleep(1)
    Robot.set_led_blue()
    matrixDisplay.showTemperatur()
    logger.debug("state request response send")
    return jsonify({'state': "Vehicle OK"})

@app.route('/dead_page')
def dead_page():
    port = request.args.get('port')
    return render_template_string("""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <title>Instance Terminated</title>
        </head>
        <body>
            <h1>This Flask instance has been terminated.</h1>
            <p>The server on port {{ port }} is no longer running.</p>
            <a href="/"><span style="font-size:28px;">Return to the main page</span></a>
        </body>
        </html>
    """, port=port)

def get_lan_ip():
    # Try to find LAN IP dynamically
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # This IP is never actually contacted; it's just to determine the local IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

print("REGISTERED ROUTES:")
print(app.url_map)
logger.debug("Start control server: " + get_lan_ip())
app.run(host='0.0.0.0', port=5000, use_reloader=False)