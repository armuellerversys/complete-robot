import time
from oled_text import OledText
import random

oledtext = OledText()

for i in range(10):
    text = "Hi-" + str(random.randint(0, 9))
    print(f"Show text: {text}")
    oledtext.show_text(text)
    time.sleep(3)