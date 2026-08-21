import time
import spidev
import lgpio
from PIL import Image

# Pin definitions (BCM Numbering)
DC_PIN = 25
RST_PIN = 27

# Initialize lgpio chip (GPIO chip 0 on Raspberry Pi 4)
chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(chip, DC_PIN)
lgpio.gpio_claim_output(chip, RST_PIN)

# Initialize SPI
spi = spidev.SpiDev()
spi.open(0, 0)  # Bus 0, Device 0 (CE0)
spi.max_speed_hz = 10000000  # 10 MHz
spi.mode = 0b00

def reset():
    lgpio.gpio_write(chip, RST_PIN, 1)
    time.sleep(0.1)
    lgpio.gpio_write(chip, RST_PIN, 0)
    time.sleep(0.1)
    lgpio.gpio_write(chip, RST_PIN, 1)
    time.sleep(0.1)

def send_cmd(cmd):
    lgpio.gpio_write(chip, DC_PIN, 0)  # Command mode
    spi.xfer2([cmd])

def send_data(data):
    lgpio.gpio_write(chip, DC_PIN, 1)  # Data mode
    if isinstance(data, int):
        spi.xfer2([data])
    else:
        spi.xfer2(list(data))

def init_display():
    reset()
    send_cmd(0xFD) # Command lock
    send_data(0x12)
    send_cmd(0xFD)
    send_data(0xB1)
    send_cmd(0xAE) # Display off

    # Column Address setup: 0 to 127
    send_cmd(0x15)
    send_data([0x00, 0x7F])

    # Row Address setup: 0 to 95 (128x96 resolution)
    send_cmd(0x75)
    send_data([0x00, 0x5F])

    # Remap & Color Depth (RGB 565, scan direction)
    send_cmd(0xA0)
    send_data([0x74])

    # Adjust Start Line & Display Offset for 128x96 Panel Offset
    send_cmd(0xA1) # Start Line
    send_data(0x00)
    
    send_cmd(0xA2) # Display Offset -> Shift by 32 rows (0x20)
    send_data(-0x20)

    send_cmd(0xB5) # Set GPIO
    send_data(0x00)
    send_cmd(0xAB) # Function Selection
    send_data(0x01)
    send_cmd(0xB1) # Phase Length
    send_data(0x32)
    send_cmd(0xBE) # VCOMH Voltage
    send_data(0x05)
    send_cmd(0xA6) # Normal Display Mode
    send_cmd(0xAF) # Display ON

def display_pil_image(image_path):
    img = Image.open(image_path).convert("RGB").resize((128, 96))
    
    buffer = []
    for y in range(96):
        for x in range(128):
            r, g, b = img.getpixel((x, y))
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buffer.append((rgb565 >> 8) & 0xFF)
            buffer.append(rgb565 & 0xFF)

    # Re-apply window limits before sending image data
    send_cmd(0x15)
    send_data([0x00, 0x7F])
    send_cmd(0x75)
    send_data([0x00, 0x5F])
    
    # Write RAM command
    send_cmd(0x5C)
    
    # Send pixel array in chunks
    chunk_size = 4096
    for i in range(0, len(buffer), chunk_size):
        send_data(buffer[i:i + chunk_size])

try:
    print("Initializing display...")
    init_display()
    print("Displaying image...")
    display_pil_image("image.png")
except Exception as e:
    print(f"An exception has occurred: {e}")
finally:
    # Cleanup GPIO chip connection on exit
    lgpio.gpiochip_close(chip)
    spi.close()