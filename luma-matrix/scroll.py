#!/usr/bin/env python3
import time
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from PIL import ImageFont

# 1. Hardware Setup
serial = spi(port=0, device=0, gpio=noop())
# Try block_orientation=-90 first. If text is scrambled, try 0 or 90.
device = max7219(serial, cascaded=4, block_orientation=-90, rotate=0)

def scroll_text(display_device, text, speed=0.05):
    # Use a default font. 'None' uses the internal luma font.
    font = ImageFont.load_default()
    
    # Calculate text width to know when to stop scrolling
    # We create a dummy canvas to measure
    with canvas(display_device) as draw:
        w, h = draw.textbbox((0, 0), text, font=font)[2:]
    
    # Start position (off-screen to the right)
    x = display_device.width
    
    # Loop until the end of the text passes the left edge
    while x > -w:
        with canvas(display_device) as draw:
            draw.text((x, 0), text, font=font, fill="white")
        
        x -= 1
        time.sleep(speed)

print("Starting Scroll... Press Ctrl+C to stop.")

try:
    while True:
        scroll_text(device, "SYSTEM ONLINE - PI 4 BLUE MATRIX", speed=0.03)
except KeyboardInterrupt:
    device.clear()