from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from time import sleep

print("Testing matrix display...")
# SPI connection
serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial, cascaded=4, block_orientation=-90)
device.contrast(5)

print("Matrix initialized.")
try:
    with canvas(device) as draw:
        print("Drawing on matrix")
        draw.text((0, -2), "--HELLO--", fill="white")
    sleep(5)
except Exception as e:
    # Handle any other exceptions
    print(f"An unexpected error occurred: {e}")
