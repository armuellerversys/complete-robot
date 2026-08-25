import time
import psutil
import socket
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import sys
import os
import logging
from waveshare_OLED import OLED_1in27_rgb

# --- Path Setup ---
tempdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'OLED-waveshare')
picdir = os.path.join(tempdir, 'pic')
libdir = os.path.join(tempdir, 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

logging.basicConfig(level=logging.INFO)

def init_display():
    logging.info("Initializing display...")
    disp = OLED_1in27_rgb.OLED_1in27_rgb()
    disp.Init()
    disp.clear()
    time.sleep(0.1)
    return disp

def get_cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
        if 'cpu_thermal' in temps:
            return temps['cpu_thermal'][0].current
    except Exception:
        pass
    return 0.0

def get_ip_address():
    """Fetches the primary active IP address of the Pi."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, used to determine local interface route
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def update_display(draw_handle, font_title, font_body, font_small):
    # Fetch live system metrics
    now_str = datetime.now().strftime("%H:%M:%S")
    cpu_usage = psutil.cpu_percent()
    cpu_temp = get_cpu_temp()
    ram = psutil.virtual_memory()
    ip_addr = get_ip_address()

    # --- Draw Canvas ---
    # Background
    draw_handle.rectangle([0, 0, 128, 96], fill=(10, 10, 15))

    # 1. Header Bar: Time
    draw_handle.rectangle([0, 0, 128, 16], fill=(30, 40, 60))
    draw_handle.text((64, 8), now_str, fill=(255, 255, 255), font=font_title, anchor="mm")

    # 2. Metrics Section
    # CPU Usage
    draw_handle.text((4, 20), f"CPU:  {cpu_usage:4.1f}%", fill=(0, 220, 255), font=font_body)
    draw_handle.rectangle([75, 23, 122, 29], outline=(60, 60, 80))
    draw_handle.rectangle([75, 23, 75 + int(0.47 * cpu_usage), 29], fill=(0, 220, 255))

    # CPU Temperature
    temp_color = (255, 85, 85) if cpu_temp > 65.0 else (85, 255, 120)
    draw_handle.text((4, 36), f"Temp: {cpu_temp:4.1f}°C", fill=temp_color, font=font_body)

    # RAM Usage
    draw_handle.text((4, 52), f"RAM:  {ram.percent:4.1f}%", fill=(255, 200, 80), font=font_body)
    draw_handle.rectangle([75, 55, 122, 61], outline=(60, 60, 80))
    draw_handle.rectangle([75, 55, 75 + int(0.47 * ram.percent), 61], fill=(255, 200, 80))

    # 3. Footer Bar: IP & Free Memory
    draw_handle.line([0, 68, 128, 68], fill=(50, 50, 65))
    draw_handle.text((4, 71), f"IP: {ip_addr}", fill=(180, 255, 180), font=font_small)
    draw_handle.text((4, 83), f"Free RAM: {ram.available / (1024**2):.0f}MB", fill=(160, 160, 180), font=font_small)

# --- Main Application Loop ---
try:
    disp = init_display()

    # Load Fonts
    try:
        font_title = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 12)
        font_body  = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 11)
        font_small = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 10)
    except IOError:
        font_title = font_body = font_small = ImageFont.load_default()

    # Create off-screen image buffer once
    image = Image.new('RGB', (disp.width, disp.height), 0)
    draw = ImageDraw.Draw(image)

    print("Dashboard running. Press Ctrl+C to exit.")

    while True:
        # 1. Redraw canvas elements
        update_display(draw, font_title, font_body, font_small)

        # 2. Render directly using Waveshare library buffer handler
        disp.ShowImage(disp.getbuffer(image))

        # Update loop delay (1 second)
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nStopping dashboard...")
finally:
    # Clear screen and turn off
    if 'disp' in locals():
        disp.clear()
        disp.command(0xAE) # Turn off display