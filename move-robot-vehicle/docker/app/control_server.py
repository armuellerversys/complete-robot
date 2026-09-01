from flask import Flask, render_template, render_template_string, jsonify, request
from robot_modes import RobotModes
from robot_gpio import Robot
from matrix_display import MatrixDisplay
import time
from datetime import datetime
from core_utils import CoreUtils
from oled_text import OledText

##
#  http://192.168.4.8:5000/
#  http://192.168.4.8:5000/state
#
##
## import debugpy
## debugpy.listen(('0.0.0.0', 5678))

# A Flask App contains all its routes.
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = False

# Prepare our robot modes for use
mode_manager = RobotModes()

Robot.set_green_one()
logger = CoreUtils.getLogger("control_server")

matrixDisplay = MatrixDisplay()

oledText = OledText()

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = "no-cache, no-store, must-revalidate"
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/")
def index():
    logger.info("index")
    matrixDisplay.showTemperature()
    return render_template('menu.html', menu=mode_manager.menu_config)

@app.route("/run/<mode_name>", methods=['POST'])
def run(mode_name):
    logger.info("route run/" + mode_name)
    Robot.set_led_white()
 
    # Use our robot app to run something with this mode_name
    try:
        mode_manager.run(mode_name)
    except Exception as e:
        logger.exception("Mode failed")
        return jsonify({"error": str(e)}), 400
    response = {'message': f'{mode_name} running'}
    if mode_manager.should_redirect(mode_name):
        response['redirect'] = True
    else:
        response['redirect'] = False
        
    ret_response = jsonify(response)
    logger.info(f"Response: {response}")
    return ret_response

@app.route("/stop_action", methods=['POST'])
def stop_action():
    logger.info("stop request received")

    Robot.safe_shutdown_devices()
    Robot.set_led_orange()
    matrixDisplay.showTemperature()
    # Tell our system to stop the mode it's in.
    mode_manager.stop()
    logger.info("Stop executed")
    return jsonify({'message': "Stopped"})

@app.route("/state", strict_slashes=False)
def state():
    logger.info("state request received")
    Robot.set_led_orange()
    time.sleep(1)
    Robot.set_led_white()
    time.sleep(1)
    Robot.set_led_blue()
    jsonTxt = show_system_state()
    logger.info("state request response send")
    return (
        jsonify({"status": "success", "message": "VEHI-SSystem parameters received successfully", "data": jsonTxt}),
        200,
    )

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

def show_system_state():

    ip = CoreUtils.get_lan_ip()
    cpu_usage = CoreUtils.get_cpu_percent()
    ram_percentage = CoreUtils.get_ram_percentage()
    ram_available = CoreUtils.get_ram_available()
    cpu_temp = CoreUtils.get_cpu_temp()

    messageLog = f"{ip}\nCPU: {cpu_usage:.1f}%\nRam: {ram_percentage:.1f}%\nFree RAM: {ram_available / (1024**2):.0f}MB\nTemp: {cpu_temp:.1f}°C"
    logger.info(f"System state: {messageLog}")
  
    return oledText.show_system_state(ip, cpu_usage, ram_percentage, ram_available, cpu_temp)

if __name__ == "__main__":
    matrixDisplay.showTemperature()
    oledText.show_text("Vehicle server ready")
    logger.info("Start control server: " + CoreUtils.get_lan_ip())
    app.run(host='0.0.0.0', port=5000, use_reloader=False)