import time
import spidev
import lgpio
import psutil
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# --- Hardware Initialization ---
DC_PIN = 24
RST_PIN = 25

chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(chip, DC_PIN)
lgpio.gpio_claim_output(chip, RST_PIN)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 10000000
spi.mode = 0b00

def reset():
    lgpio.gpio_write(chip, RST_PIN, 1)
    time.sleep(0.05)
    lgpio.gpio_write(chip, RST_PIN, 0)
    time.sleep(0.05)
    lgpio.gpio_write(chip, RST_PIN, 1)
    time.sleep(0.05)

def send_cmd(cmd):
    lgpio.gpio_write(chip, DC_PIN, 0)
    spi.xfer2([cmd])

def send_data(data):
    lgpio.gpio_write(chip, DC_PIN, 1)
    if isinstance(data, int):
        spi.xfer2([data])
    else:
        spi.xfer2(list(data))

def init_display():
    reset()
    send_cmd(0xFD); send_data(0x12)
    send_cmd(0xFD); send_data(0xB1)
    send_cmd(0xAE) # Display off
    send_cmd(0x15); send_data([0x00, 0x7F]) # Columns 0-127
    send_cmd(0x75); send_data([0x00, 0x5F]) # Rows 0-95
    send_cmd(0xA0); send_data([0x74])       # Color depth
    send_cmd(0xA1); send_data(0x00)       # Start line
    send_cmd(0xA2); send_data(-0x20 & 0xFF) # Display offset
    send_cmd(0xB5); send_data(0x00)
    send_cmd(0xAB); send_data(0x01)
    send_cmd(0xB1); send_data(0x32)
    send_cmd(0xBE); send_data(0x05)
    send_cmd(0xA6) # Normal display
    send_cmd(0xAF) # Display ON

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
    init_display()

    # Load Fonts
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 10)
    except IOError:
        font_title = font_body = ImageFont.load_default()

    # Create image buffer in memory once
    image = Image.new("RGB", (128, 96))
    draw = ImageDraw.Draw(image)

    print("Dashboard running. Press Ctrl+C to exit.")
    
    while True:
        # 1. Update image canvas
        update_display(draw, font_title, font_body)

        # 2. Convert Pillow canvas to RGB565 byte array
        buffer = []
        for y in range(96):
            for x in range(128):
                r, g, b = image.getpixel((x, y))
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                buffer.append((rgb565 >> 8) & 0xFF)
                buffer.append(rgb565 & 0xFF)

        # 3. Transmit buffer over SPI
        send_cmd(0x15); send_data([0x00, 0x7F])
        send_cmd(0x75); send_data([0x00, 0x5F])
        send_cmd(0x5C)

        chunk_size = 4096
        for i in range(0, len(buffer), chunk_size):
            send_data(buffer[i:i + chunk_size])

        # Frame rate control (updates every 1.0 second)
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nStopping dashboard...")
finally:
    # Clear screen and free hardware resource
    image_black = Image.new("RGB", (128, 96), (0, 0, 0))
    send_cmd(0xAE) # Turn off screen
    lgpio.gpiochip_close(chip)
    spi.close()