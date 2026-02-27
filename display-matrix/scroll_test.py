
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.led_matrix.device import max7219
from luma.core.virtual import viewport
from PIL import ImageFont
import time

current_message = "READY for scrolling"

# --- Setup Display ---
serial = spi(port=0, device=0, gpio_coords=True)
# Adjust 'cascaded' to the number of 8x8 blocks you have (4 for an 8x32)
device = max7219(serial, cascaded=4, block_orientation=-90, rotate=0)
device.contrast(40) # Keep it dim for 24/7 use
virtual = viewport(device, width=200, height=8) # Large virtual width for scrolling
print("Matrix display initialized.")

print("Display mode: scroll with message: {}".format(current_message))
# 1. Draw the full message on the virtual "long" canvas
with canvas(virtual) as draw:
    draw.text((0, -2), current_message, fill="white")

# 2. Calculate how far we need to scroll
# Roughly 6 pixels per character
msg_width = len(current_message) * 6 

# 3. Scroll until a new message arrives
for x in range(msg_width + device.width):
    virtual.set_position((x, 0))
    time.sleep(0.05) # Adjust for scroll speed


print("Display mode: static with message: {}".format(current_message))       
with canvas(device) as draw:
    draw.text((0, -2), current_message, fill="white")

time.sleep(2)

# Load a pixel-perfect font
# You can download 'tiny.ttf' or similar and place it in your script folder
try:
    # 8 is the size in pixels
    pixel_font = ImageFont.truetype("pixelmix.ttf", 8) 
except IOError:
    # Fallback to default if font file is missing
    pixel_font = None 

# Using a font object here makes it proportional automatically
draw.text((0, -1), current_message, fill="white", font=pixel_font)

while True:
    time.sleep(1)
