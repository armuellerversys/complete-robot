import threading
import time
from flask import Flask, request, render_template_string
import logging
import sys
import subprocess
from matrix11x7 import Matrix11x7
from matrix11x7.fonts import font5x7 as font5x7
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.led_matrix.device import max7219
from luma.core.virtual import viewport
from PIL import ImageFont

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a handler that writes to the system's standard output
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
current_font_path = "font/pixelmix.ttf"

# --- Setup Display ---
serial = spi(port=0, device=0, gpio_coords=True)
# Adjust 'cascaded' to the number of 8x8 blocks you have (4 for an 8x32)
device = max7219(serial, cascaded=4, block_orientation=-90, rotate=0)
device.contrast(40) # Keep it dim for 24/7 use
virtual = viewport(device, width=200, height=8) # Large virtual width for scrolling
matrix11x7 = Matrix11x7(None, 0x77)
matrix11x7.set_brightness(0.5)
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
    global current_message, display_mode, new_data_available
    data = request.get_json()
    
    if data and 'message' in data:
        current_message = data['message']
        # Default to static if not specified
        display_mode = data.get('mode', 'static') 
        new_data_available = True
        logger.info("Showing updated message: {}".format(current_message))
        return {"status": "updated", "msg": current_message, "mode": display_mode}, 200
    
    return {"status": "error", "reason": "invalid data"}, 400

@app.route('/showChar', methods=['POST'])
def show_char():
    global current_message, server_requ
    new_msg = request.json.get('message', 'No Message')
    matrix11x7.clear()  
    matrix11x7.write_string(new_msg)
    # Show the buffer
    matrix11x7.show()
    logger.info(f"Updated message to: {new_msg}")
    return {"status": "success", "updated_to": new_msg}, 200

@app.route('/reset', methods=['POST'])
def reset_display():
    global current_message, display_mode, new_data_available
    logger.info("Resetting display (clearing matrix).")
    
    current_message = ""      # Empty string clears the text
    display_mode = "static"   # Stop any active scrolling
    new_data_available = True # Force the loop to update once
    
    return {"status": "success", "message": "Display cleared"}, 200

@app.route('/brightness', methods=['POST'])
def set_brightness():
    data = request.get_json()
    if not data or 'level' not in data:
        return {"status": "error", "reason": "Missing 'level' (0-255)"}, 400
    
    level = int(data['level'])
    # Clamp the value between 0 and 255 to prevent errors
    level = max(0, min(255, level))
    
    device.contrast(level)
    logger.info(f"Brightness set to: {level}")
    return {"status": "success", "new_level": level}, 200

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

@app.route('/font', methods=['POST'])
def change_font():
    global current_font_path, pixel_font, new_data_available
    data = request.get_json()
    # Assume fonts are stored in a /fonts folder
    current_font_path = f"fonts/{data['font_name']}.ttf"
    pixel_font = ImageFont.truetype(current_font_path, 8)
    new_data_available = True
    return {"status": "font changed"}

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

def draw_text_centered(draw, message):
    # Using a font object here makes it proportional automatically
    draw.text((0, -1), message, fill="white", font=pixel_font)

def show_status():
    global current_message, display_mode, new_data_available, pixel_font
    
    while True:
        if display_mode == "static":
            if new_data_available:
                with canvas(device) as draw:
                    # Drawing "" clears the display
                    draw.text((0, 0), current_message, fill="white", font=pixel_font)
                new_data_available = False
            time.sleep(0.2)

        elif display_mode == "scroll":
            with canvas(virtual) as draw:
                # Use the font object here
                draw.text((0, 0), current_message, fill="white", font=pixel_font)
            
            # Get the actual pixel width of the rendered text
            if pixel_font:
                # anchor="lt" means left-top alignment
                left, top, right, bottom = pixel_font.getbbox(current_message)
                msg_width = right
            else:
                msg_width = len(current_message) * 6

            for x in range(msg_width + device.width):
                if new_data_available: 
                    break 
                virtual.set_position((x, 0))
                time.sleep(0.05)

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