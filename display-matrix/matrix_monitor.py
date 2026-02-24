from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.legacy import show_message
from luma.core.legacy.font import proportional, LCD_FONT

import psutil
import socket
import time
import subprocess

# SPI setup
serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial, cascaded=4, block_orientation=-90)

device.contrast(5)   # brightness 0-255

def get_cpu_temp():
    try:
        temp = subprocess.check_output(
            ["vcgencmd", "measure_temp"]
        ).decode()
        return temp.replace("temp=", "").replace("'C\n", "")
    except:
        return "N/A"

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "NoNet"

def get_stats():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    temp = get_cpu_temp()
    host = socket.gethostname()
    ip = get_ip()

    return f"{host}  CPU:{cpu:.0f}%  RAM:{ram:.0f}%  TEMP:{temp}C  IP:{ip}  "

while True:
    msg = get_stats()
    show_message(
        device,
        msg,
        fill="white",
        font=proportional(LCD_FONT),
        scroll_delay=0.05,
        y_offset=2
    )
    time.sleep(1)