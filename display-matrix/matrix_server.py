import threading
from flask import Flask, request
import time
import subprocess
import os
import logging
from matrix11x7 import Matrix11x7
from matrix11x7.fonts import font5x7 as font5x7
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from PIL import ImageFont

logger = logging.getLogger(__name__)
# 1. Hardware Setup
serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial, cascaded=4, block_orientation=-90, rotate=0)
device.contrast(40) # Keep it dim for 24/7 use
current_message = None
server_requ = False
matrix11x7 = Matrix11x7(None, 0x77)
matrix11x7.set_brightness(0.5)


# This is required for the Flask server to run properly in a separate process
# from the OVOS bus client
if __name__ == "__main__":
    app = Flask(__name__)
else:
    app = Flask(__name__)

@app.route('/showText', methods=['POST'])
def show_text():
    global current_message, server_requ
    new_msg = request.json.get('message', 'No Message')
    current_message = new_msg
    server_requ = True
    logger.info(f"Updated message to: {new_msg}")
    print(f"Updated message to: {new_msg}")
    return {"status": "success", "updated_to": new_msg}, 200

@app.route('/showChar', methods=['POST'])
def show_Char():
    global current_message, server_requ
    new_msg = request.json.get('message', 'No Message')
    matrix11x7.clear()  
    matrix11x7.write_string(new_msg)
    # Show the buffer
    matrix11x7.show()
    logger.info(f"Updated message to: {new_msg}")
    return {"status": "success", "updated_to": new_msg}, 200

@app.route('/resetDisplay', methods=['POST'])
def reset_display():
    global current_message, server_requ
    current_message = None
    server_requ = False
    matrix11x7.clear()
    matrix11x7.show()
    return {"status": "success", "updated_to": "message cleared"}, 200
   
def get_ip():
    try:
        # Gets the primary local IP address
        cmd = "hostname -I | cut -d' ' -f1"
        return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    except:
        return "No IP"

def get_temp():
    try:
        # Reads the Pi's SoC temperature
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_raw = int(f.read())
        return f"{temp_raw / 1000:.1f}C"
    except:
        return "0.0C"

def scroll_message(device, text, speed=0.2):
    global current_message, server_requ

    font = ImageFont.load_default()

    with canvas(device) as draw:
        w, h = draw.textbbox((0, -2), text, font=font)[2:]

    x = device.width

    while x > -w:
        # stop scrolling if a new server message arrives
        if server_requ and text != current_message:
            return

        with canvas(device) as draw:
            draw.text((x, -2), text, font=font, fill="white")

        x -= 1
        time.sleep(speed)

def show_status():
    global current_message, server_requ

    while True:
        if server_requ and current_message:
            msg = current_message
        else:
            ip = get_ip()
            temp = get_temp()
            msg = f"IP:{ip} T:{temp}"

        scroll_message(device, msg)

def run_flask():
    # We set use_reloader=False because the reloader creates 
    # a child process that doesn't play nice with threads.
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    # We'll set up a startup message
    startup_message = f"Start matrix server: {os.environ.get('FLASK_RUN_HOST', '127.0.0.1')}"
    logger.info(startup_message)
    logger.info(f"Process-PID: {os.getpid()}")

    # 1. Create a thread specifically for the Flask app
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    
    # 2. Start the thread
    flask_thread.start()

    # 3. Now the main thread is free to run your loop
    show_status()