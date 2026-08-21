import time
import spidev
import lgpio
from PIL import Image, ImageDraw, ImageFont

# Pin definitions (BCM Numbering)
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
    time.sleep(0.1)
    lgpio.gpio_write(chip, RST_PIN, 0)
    time.sleep(0.1)
    lgpio.gpio_write(chip, RST_PIN, 1)
    time.sleep(0.1)

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
    send_cmd(0x15); send_data([0x00, 0x7F]) # Columns
    send_cmd(0x75); send_data([0x00, 0x5F]) # Rows
    send_cmd(0xA0); send_data([0x74])       # Color depth / Remap
    send_cmd(0xA1); send_data(0x00)       # Start line
    send_cmd(0xA2); send_data(-0x20 & 0xFF) # Your adjusted offset
    send_cmd(0xB5); send_data(0x00)
    send_cmd(0xAB); send_data(0x01)
    send_cmd(0xB1); send_data(0x32)
    send_cmd(0xBE); send_data(0x05)
    send_cmd(0xA6) # Normal Display
    send_cmd(0xAF) # Display ON

def draw_text_screen():
    # 1. Create a blank image canvas with dark background
    image = Image.new("RGB", (128, 96), (15, 15, 20))
    draw = ImageDraw.Draw(image)

    # 2. Load TTF fonts (fall back to default if font missing)
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except IOError:
        title_font = body_font = ImageFont.load_default()

    # 3. Draw shapes & text onto the image
    # Top header bar
    draw.rectangle([0, 0, 128, 20], fill=(0, 102, 204))
    draw.text((64, 10), "RASPBERRY PI", fill=(255, 255, 255), font=title_font, anchor="mm")

    # Content lines (RGB colors: Red, Green, Cyan)
    draw.text((10, 30), "OLED: 1.27 Inch", fill=(255, 85, 85), font=body_font)
    draw.text((10, 48), "Driver: SSD1351", fill=(85, 255, 85), font=body_font)
    draw.text((10, 66), "Lib: lgpio + SPI", fill=(85, 255, 255), font=body_font)

    # 4. Convert canvas to RGB565 buffer format
    buffer = []
    for y in range(96):
        for x in range(128):
            r, g, b = image.getpixel((x, y))
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buffer.append((rgb565 >> 8) & 0xFF)
            buffer.append(rgb565 & 0xFF)

    # 5. Push buffer to OLED RAM
    send_cmd(0x15); send_data([0x00, 0x7F])
    send_cmd(0x75); send_data([0x00, 0x5F])
    send_cmd(0x5C)

    chunk_size = 4096
    for i in range(0, len(buffer), chunk_size):
        send_data(buffer[i:i + chunk_size])

try:
    init_display()
    draw_text_screen()
finally:
    lgpio.gpiochip_close(chip)
    spi.close()