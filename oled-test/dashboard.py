import time
import lgpio
import psutil
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import sys
import os
import logging
from waveshare_OLED import OLED_1in27_rgb

tempdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'OLED-waveshare')
picdir = os.path.join(tempdir, 'pic')
libdir = os.path.join(tempdir, 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

logging.basicConfig(level=logging.DEBUG)

def init_display():
    logging.info("init display")
    disp = OLED_1in27_rgb.OLED_1in27_rgb()
    disp.Init()
    # Clear display.
    logging.info("clear display")
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

def update_display(draw_handle, font_title, font_body):
    # Fetch live system metrics
    now_str = datetime.now().strftime("%H:%M:%S")
    cpu_usage = psutil.cpu_percent()
    cpu_temp = get_cpu_temp()
    ram = psutil.virtual_memory()

    # --- Draw Canvas ---
    # Background
    draw_handle.rectangle([0, 0, 128, 96], fill=(10, 10, 15))

    # Header Bar: Time
    draw_handle.rectangle([0, 0, 128, 18], fill=(30, 40, 60))
    draw_handle.text((64, 9), now_str, fill=(255, 255, 255), font=font_title, anchor="mm")

    # Metrics Section
    # 1. CPU Usage
    draw_handle.text((6, 24), f"CPU:  {cpu_usage:4.1f}%", fill=(0, 220, 255), font=font_body)
    draw_handle.rectangle([75, 27, 120, 33], outline=(60, 60, 80))
    draw_handle.rectangle([75, 27, 75 + int(0.45 * cpu_usage), 33], fill=(0, 220, 255))

    # 2. CPU Temperature
    # Change color to red if temperature exceeds 65°C
    temp_color = (255, 85, 85) if cpu_temp > 65.0 else (85, 255, 120)
    draw_handle.text((6, 42), f"Temp: {cpu_temp:4.1f}°C", fill=temp_color, font=font_body)

    # 3. RAM Usage
    draw_handle.text((6, 60), f"RAM:  {ram.percent:4.1f}%", fill=(255, 200, 80), font=font_body)
    draw_handle.rectangle([75, 63, 120, 69], outline=(60, 60, 80))
    draw_handle.rectangle([75, 63, 75 + int(0.45 * ram.percent), 69], fill=(255, 200, 80))

    # Footer Bar
    draw_handle.line([0, 80, 128, 80], fill=(50, 50, 65))
    draw_handle.text((6, 84), f"Free: {ram.available / (1024**2):.0f}MB", fill=(160, 160, 180), font=font_body)

# --- Main Application Loop ---
try:
    disp = init_display()

    # Load Fonts
    try:
        font_body = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 12)
        font_title = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
        font_large = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    except IOError:
        font_title = font_body = ImageFont.load_default()

    # Create image buffer in memory once
    image = Image.new('RGB', (disp.width, disp.height), 0)
    draw = ImageDraw.Draw(image)

    print("Dashboard running. Press Ctrl+C to exit.")

    logging.info ("***draw line")
    draw.line([(0,0),(127,0)], fill = "RED")
    draw.line([(0,0),(0,95)], fill = "RED")
    draw.line([(0,95),(127,95)], fill = "RED")
    draw.line([(127,0),(127,95)], fill = "RED")
    
    while True:
        # 1. Update image canvas
        update_display(draw, font_title, font_body)

        # 2. Convert Pillow canvas to RGB565 byte array
        buffer = []
        for y in range(disp.height):
            for x in range(disp.width):
                r, g, b = image.getpixel((x, y))
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                buffer.append((rgb565 >> 8) & 0xFF)
                buffer.append(rgb565 & 0xFF)

        # 3. Transmit buffer over SPI
        disp.command(0x15); 
        disp.data(0x00)
        disp.data(0x7F)
        disp.command(0x75); 
        disp.data(0x00)
        disp.data(0x5F)
        disp.command(0x5C)

        chunk_size = 4096
        for i in range(0, len(buffer), chunk_size):
            tmp_chunk = buffer[i:i + chunk_size]
            disp.data(tmp_chunk[0])
            disp.data(tmp_chunk[1])

        disp.ShowImage(disp.getbuffer(image))
        # Frame rate control (updates every 1.0 second)
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nStopping dashboard...")
finally:
    # Clear screen and free hardware resource
    image_black = Image.new("RGB", (128, 96), (0, 0, 0))
    disp.command(0xAE) # Turn off screen
