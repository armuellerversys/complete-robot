#!/usr/bin/python3

import time
import spidev
import lgpio

DC_PIN = 24
RST_PIN = 25

chip = lgpio.gpiochip_open(0)

lgpio.gpio_claim_output(chip, DC_PIN, 0)
lgpio.gpio_claim_output(chip, RST_PIN, 1)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 8000000
spi.mode = 0


def cmd(value):
    lgpio.gpio_write(chip, DC_PIN, 0)
    spi.xfer2([value])


def data(value):
    lgpio.gpio_write(chip, DC_PIN, 1)

    if isinstance(value, int):
        spi.xfer2([value])
    else:
        spi.xfer2(list(value))


def reset():
    lgpio.gpio_write(chip, RST_PIN, 1)
    time.sleep(0.1)

    lgpio.gpio_write(chip, RST_PIN, 0)
    time.sleep(0.1)

    lgpio.gpio_write(chip, RST_PIN, 1)
    time.sleep(0.1)


def init_display():

    reset()

    # Command unlock
    cmd(0xFD)
    data(0x12)

    cmd(0xFD)
    data(0xB1)

    # Display OFF
    cmd(0xAE)

    # Clock divider
    cmd(0xB3)
    data(0xF1)

    # Multiplex ratio
    cmd(0xCA)
    data(0x5F)       # 96 rows

    # Display offset
    cmd(0xA2)
    data(0x00)

    # Start line
    cmd(0xA1)
    data(0x00)

    # Remap / RGB565
    cmd(0xA0)
    data(0x74)

    # GPIO
    cmd(0xB5)
    data(0x00)

    # Function selection
    cmd(0xAB)
    data(0x01)

    # Pre-charge
    cmd(0xB1)
    data(0x32)

    # Pre-charge voltage
    cmd(0xBB)
    data(0x17)

    # VCOMH
    cmd(0xBE)
    data(0x05)

    # Master current
    cmd(0xC1)
    data([0xC8, 0x80, 0xC8])

    # Contrast
    cmd(0xC7)
    data(0x0F)

    # Normal display
    cmd(0xA6)

    # Display ON
    cmd(0xAF)

    time.sleep(0.1)


def fill_screen(r, g, b):

    rgb565 = ((r & 0xF8) << 8) | \
             ((g & 0xFC) << 3) | \
             (b >> 3)

    hi = (rgb565 >> 8) & 0xFF
    lo = rgb565 & 0xFF

    # Column address
    cmd(0x15)
    data([0x00, 0x7F])

    # Row address
    cmd(0x75)
    data([0x00, 0x5F])

    # Write RAM
    cmd(0x5C)

    # 128 x 96 pixels
    pixels = bytes([hi, lo]) * (128 * 96)

    # Send in manageable chunks
    lgpio.gpio_write(chip, DC_PIN, 1)

    for i in range(0, len(pixels), 4096):
        spi.xfer2(list(pixels[i:i+4096]))


try:

    print("Initializing OLED...")
    init_display()

    print("RED")
    fill_screen(255, 0, 0)
    time.sleep(2)

    print("GREEN")
    fill_screen(0, 255, 0)
    time.sleep(2)

    print("BLUE")
    fill_screen(0, 0, 255)
    time.sleep(2)

    print("WHITE")
    fill_screen(255, 255, 255)
    time.sleep(2)

    print("BLACK")
    fill_screen(0, 0, 0)
    time.sleep(2)

finally:

    cmd(0xAE)

    spi.close()
    lgpio.gpiochip_close(chip)