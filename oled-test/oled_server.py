import threading
import time
from flask import Flask, request, render_template_string
import logging
import sys
import subprocess
import display_oled
from PIL import ImageFont

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a handler that writes to the system's standard output
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
current_font_path = "font/pixelmix.ttf"

# --- Setup Display ---
displayOledText = display_oled.DisplayOledText()
logger.info("Matrix display initialized.")

app = Flask(__name__)

# Shared state
current_message = "READY"
display_mode = "static" # "static" or "scroll"
new_data_available = True 

# Load a pixel-perfect font
# You can download 'tiny.ttf' or similar and place it in your script folder
try:
    # 8 is the size in pixels
    pixel_font = ImageFont.truetype(current_font_path, 8) 
except IOError:
    # Fallback to default if font file is missing
    pixel_font = None
    logger.error("Error accessing font file: {}".format(current_font_path))

@app.route('/showText', methods=['POST'])
def update_display():
    return {"status": "error", "reason": "invalid data"}, 400

@app.route('/showChar', methods=['POST'])
def show_char():
    return {"status": "success", "updated_to": "new_msg"}, 200

@app.route('/reset', methods=['POST'])
def reset_display():
    return {"status": "success", "message": "Display cleared"}, 200

from flask import render_template_string

@app.route('/')
def dashboard():
    # A simple, mobile-friendly HTML interface
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Matrix Control</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; text-align: center; padding: 20px; background: #222; color: #fff; }
            input, button, select { padding: 10px; margin: 10px; font-size: 16px; border-radius: 5px; border: none; }
            button { background: #007bff; color: white; cursor: pointer; width: 80%; max-width: 300px; }
            .reset { background: #dc3545; }
            input[type="text"] { width: 80%; max-width: 300px; }
        </style>
    </head>
    <body>
        <h2>Matrix Controller</h2>
        
        <input type="text" id="msg" placeholder="Type message here...">
        <br>
        <select id="mode">
            <option value="static">Static</option>
            <option value="scroll">Scroll</option>
        </select>
        <br>
        <button onclick="sendUpdate()">Update Display</button>
        <br>
        <hr>
        <p>Brightness (0-255)</p>
        <input type="range" id="bright" min="0" max="255" value="40" onchange="sendBright(this.value)">
        <br>
        <button class="reset" onclick="reset()">Clear Matrix</button>

        <script>
            function sendUpdate() {
                const msg = document.getElementById('msg').value;
                const mode = document.getElementById('mode').value;
                fetch('/showText', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg, mode: mode})
                });
            }

            function sendBright(val) {
                fetch('/brightness', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({level: val})
                });
            }

            function reset() {
                fetch('/reset', { method: 'POST' });
            }
        </script>
    </body>
    </html>
    ''')

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

def show_startup_status():
    global current_message, display_mode, new_data_available
    ip = get_ip()
    temp = get_temp()
    current_message = f"IP:{ip} T:{temp}"
    display_mode = "scroll"
    new_data_available = True
    show_status()
    logger.info("Showing default status message.")

def run_flask():
    # We set use_reloader=False because the reloader creates 
    # a child process that doesn't play nice with threads.
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    show_startup_status()

    flask_thread.join()  