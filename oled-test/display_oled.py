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

class DisplayOledText:
    def __init__(self):
        self.chip = chip
        self.spi = spi

    def reset(self):
        lgpio.gpio_write(self.chip, RST_PIN, 1)
        time.sleep(0.1)
        lgpio.gpio_write(self.chip, RST_PIN, 0)
        time.sleep(0.1)
        lgpio.gpio_write(self.chip, RST_PIN, 1)
        time.sleep(0.1)

    def send_cmd(self, cmd):
        lgpio.gpio_write(self.chip, DC_PIN, 0)
        self.spi.xfer2([cmd])

    def send_data(self, data):
        lgpio.gpio_write(chip, DC_PIN, 1)
        if isinstance(data, int):
            spi.xfer2([data])
        else:
            spi.xfer2(list(data))

    def init_display(self):
        self.reset()
        self.send_cmd(0xFD) # Command lock
        self.send_data(0x12)
        self.send_cmd(0xFD)
        self.send_data(0xB1)
        self.send_cmd(0xAE) # Display off
    
        # Column Address setup: 0 to 127
        self.send_cmd(0x15)
        self.send_data([0x00, 0x7F])
    
        # Row Address setup: 0 to 95 (128x96 resolution)
        self.send_cmd(0x75)
        self.send_data([0x00, 0x5F])
    
        # Remap & Color Depth (RGB 565, scan direction)
        self.send_cmd(0xA0)
        self.send_data([0x74])
    
        # Adjust Start Line & Display Offset for 128x96 Panel Offset
        self.send_cmd(0xA1) # Start Line
        self.send_data(0x00)
        
        self.send_cmd(0xA2) # Display Offset -> Shift by 32 rows (0x20)
        self.send_data(-0x20 & 0xFF)
    
        self.send_cmd(0xB5) # Set GPIO
        self.send_data(0x00)
        self.send_cmd(0xAB) # Function Selection
        self.send_data(0x01)
        self.send_cmd(0xB1) # Phase Length
        self.send_data(0x32)
        self.send_cmd(0xBE) # VCOMH Voltage
        self.send_data(0x05)
        self.send_cmd(0xA6) # Normal Display Mode
        self.send_cmd(0xAF) # Display ON


    def draw_text_screen(self, text="Hello, OLED!", font_size=16):
        # 1. Create a blank image canvas with dark background
        image = Image.new("RGB", (128, 96), (15, 15, 20))
        draw = ImageDraw.Draw(image)

        # 2. Load TTF fonts (fall back to default if font missing)
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size - 3)
        except IOError:
            title_font = body_font = ImageFont.load_default()

        # 3. Draw shapes & text onto the image
        # Top header bar
        draw.rectangle([0, 0, 128, 20], fill=(0, 102, 204))
        draw.text((64, 10), text, fill=(255, 255, 255), font=title_font, anchor="mm")

        # 4. Convert canvas to RGB565 buffer format
        buffer = []
        for y in range(96):
            for x in range(128):
                r, g, b = image.getpixel((x, y))
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                buffer.append((rgb565 >> 8) & 0xFF)
                buffer.append(rgb565 & 0xFF)

        # 5. Push buffer to OLED RAM
        self.send_cmd(0x15); self.send_data([0x00, 0x7F])
        self.send_cmd(0x75); self.send_data([0x00, 0x5F])
        self.send_cmd(0x5C)

        chunk_size = 4096
        for i in range(0, len(buffer), chunk_size):
            self.send_data(buffer[i:i + chunk_size])

    def display_state(self):
        self.draw_text_screen("OLED: 1.27 Inch")
        self.draw_text_screen("Driver: SSD1351")
        self.draw_text_screen("Lib: lgpio + SPI")

    def close(self):
        self.spi.close()
        lgpio.gpiochip_close(self.chip)
