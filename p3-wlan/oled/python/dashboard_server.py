import time
import psutil
import socket
from matrix11x7 import Matrix11x7
from matrix11x7.fonts import font5x7 as font5x7
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import sys
import os
import logging
import threading
from flask import Flask, request, jsonify
from waveshare_OLED import OLED_1in27_rgb
##
# curl -X POST http://192.168.178.61:5000/displayText \
#     -H "Content-Type: application/json" \
#     -d '{"header": "ALERT", "message": "Server backup complete!"}'
##
##
# curl -X POST http://192.168.178.61:5000/displayDashboard
##

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(levelname)s: %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("OLED monitoring started")

# --- Path Setup ---
tempdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'OLED-waveshare')
picdir = os.path.join(tempdir, 'pic')
libdir = os.path.join(tempdir, 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

matrix11x7 = Matrix11x7(None, 0x77)
matrix11x7.set_brightness(0.5)
logger.info("Matrix11x7 display initialized.")

# --- App State & Flask Setup ---
app = Flask(__name__)

# State lock and mode control ('dashboard' or 'text')
display_mode = "dashboard"
current_header = ""
current_message = ""
mode_lock = threading.Lock()

# Global hardware objects
disp = None
image = None
draw = None
font_title = None
font_body = None
font_small = None
font_large = None

def init_display():
    global disp, image, draw, font_title, font_body, font_small, font_large
    logger.info("Initializing OLED display...")
    disp = OLED_1in27_rgb.OLED_1in27_rgb()
    disp.Init()
    disp.clear()
    time.sleep(0.1)

    # Load Fonts
    try:
        font_title = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 12)
        font_body  = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 11)
        font_small = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 10)
        font_large = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 14)
    except IOError:
        font_title = font_body = font_small = font_large = ImageFont.load_default()

    image = Image.new('RGB', (disp.width, disp.height), 0)
    draw = ImageDraw.Draw(image)

def get_cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
        if 'cpu_thermal' in temps:
            return temps['cpu_thermal'][0].current
    except Exception:
        pass
    return 0.0

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def display_dashboard():
    now_str = datetime.now().strftime("%H:%M:%S")
    cpu_usage = psutil.cpu_percent()
    cpu_temp = get_cpu_temp()
    ram = psutil.virtual_memory()
    ip_addr = get_ip_address()
    render_dashboard(now_str, cpu_usage, cpu_temp, ram.percent, ram.available, ip_addr)

def render_dashboard(now_str, cpu_usage, cpu_temp, ram_percentage, ram_available, ip_addr):
    # Clear Canvas
    draw.rectangle([0, 0, 128, 96], fill=(10, 10, 15))
    # Clear Canvas
    draw.rectangle([0, 0, 128, 96], fill=(0, 0, 0))

    # Header Bar: Time
    draw.rectangle([0, 0, 128, 16], fill=(30, 40, 60))
    draw.text((64, 8), now_str, fill=(255, 255, 255), font=font_title, anchor="mm")

    # Metrics
    draw.text((4, 20), f"CPU:  {cpu_usage:4.1f}%", fill=(0, 220, 255), font=font_body)
    draw.rectangle([75, 23, 122, 29], outline=(60, 60, 80))
    draw.rectangle([75, 23, 75 + int(0.47 * cpu_usage), 29], fill=(0, 220, 255))

    temp_color = (255, 85, 85) if cpu_temp > 65.0 else (85, 255, 120)
    draw.text((4, 36), f"Temp: {cpu_temp:4.1f}°C", fill=temp_color, font=font_body)

    draw.text((4, 52), f"RAM:  {ram_percentage:4.1f}%", fill=(255, 200, 80), font=font_body)
    draw.rectangle([75, 55, 122, 61], outline=(60, 60, 80))
    draw.rectangle([75, 55, 75 + int(0.47 * ram_percentage), 61], fill=(255, 200, 80))

    # Footer
    draw.line([0, 68, 128, 68], fill=(50, 50, 65))
    draw.text((4, 71), f"IP: {ip_addr}", fill=(180, 255, 180), font=font_small)
    draw.text((4, 83), f"Free RAM: {ram_available/ (1024**2):.0f}MB", fill=(160, 160, 180), font=font_small)

def render_custom_text(header, message):
    # Clear Canvas
    draw.rectangle([0, 0, 128, 96], fill=(0, 0, 0))

    # Render Header Banner
    draw.rectangle([0, 0, 128, 22], fill=(0, 102, 204))
    draw.text((64, 11), header[:15], fill=(255, 255, 255), font=font_large, anchor="mm")

    # Render Multi-line Message Box (simple word wrapping)
    words = message.split(' ')
    lines = []
    current_line = ""
    for word in words:
        if len(current_line + " " + word) <= 18:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    # Draw max 4 lines of text message
    y_offset = 30
    for line in lines[:4]:
        draw.text((6, y_offset), line, fill=(255, 255, 255), font=font_body)
        y_offset += 15

# --- Background Refresh Worker ---
def display_worker():
    while True:
        with mode_lock:
            if display_mode == "dashboard":
                display_dashboard()
            elif display_mode == "text":
                render_custom_text(current_header, current_message)
            
            # Send current canvas to hardware
            disp.ShowImage(disp.getbuffer(image))

        time.sleep(1.0)

# --- Flask Endpoints ---
@app.route('/displayText', methods=['POST'])
def api_display_text():
    global display_mode, current_header, current_message
    data = request.get_json(silent=True) or request.form

    header = data.get('header', 'MESSAGE')
    message = data.get('message', '')
    logger.info(f"Received displayText request: header='{header}', message='{message}'")
    if not message:
        return jsonify({"status": "error", "message": "Field 'message' is required"}), 400

    with mode_lock:
        current_header = header
        current_message = message
        display_mode = "text"
        disp.clear()

    return jsonify({"status": "success", "mode": "text", "header": header, "message": message})

@app.route('/displaySysParms', methods=['POST'])
def api_display_sys_parms():

    # Parse incoming JSON payload
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "No JSON data provided"}), 400

    # Extract the required parameters
    ip = data.get("IP")
    cpu = data.get("CPU")
    mem_percentage = data.get("MEM_PERCENT")
    mem_available = data.get("MEM_AVAILABLE")
    # date = data.get("DATE")
    date = "data"
    temp = data.get("TEMP")

    # Process or log the received parameters
    logger.info(
        f"Received Metrics -> IP: {ip} | CPU: {cpu}% | MEM: {mem_percentage}% | Free RAM: {mem_available / (1024**2):.0f}MB | DATE: {date} | TEMP: {temp}°C"
    )
    
    disp.clear()
    render_dashboard(date, cpu, temp, mem_percentage, mem_available, ip)
    return (
        jsonify({"status": "success", "message": "OLED-System parameters received successfully"}),
        200,
    )

@app.route('/displayDashboard', methods=['POST', 'GET'])
def api_display_dashboard():
    global display_mode
    with mode_lock:
        display_mode = "dashboard"
        disp.clear()

    return jsonify({"status": "success", "mode": "dashboard"})

@app.route('/showChar', methods=['POST'])
def show_char():
    new_msg = request.json.get('message', 'No Message')
    matrix11x7.clear()  
    matrix11x7.write_string(new_msg)
    # Show the buffer
    matrix11x7.show()
    logger.info(f"Updated message to: {new_msg}")
    return {"status": "success", "updated_to": new_msg}, 200

@app.route('/testChar', methods=['GET'])
def test_char():
    matrix11x7.clear()  
    matrix11x7.write_string("Test")
    # Show the buffer
    matrix11x7.show()
    logger.info("testChar endpoint called, displaying 'Test'")
    return {"status": "success", "updated_to": "Test"}, 200

if __name__ == '__main__':
    # 1. Initialize hardware
    init_display()

    # 2. Start screen update thread
    worker_thread = threading.Thread(target=display_worker, daemon=True)
    worker_thread.start()

    # 3. Start Web API Server on port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)