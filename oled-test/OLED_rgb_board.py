#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
import os
tempdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'OLED-waveshare')
picdir = os.path.join(tempdir, 'pic')
libdir = os.path.join(tempdir, 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging    
import time
import traceback
from waveshare_OLED import OLED_1in27_rgb
from PIL import Image,ImageDraw,ImageFont
logging.basicConfig(level=logging.DEBUG)

try:
    disp = OLED_1in27_rgb.OLED_1in27_rgb()
    logging.info(f"Temp directory: {tempdir}")
    logging.info("\r 1.27inch rgb OLED ")
    # Initialize library.
    disp.Init()
    # Clear display.
    logging.info("clear display")
    disp.clear()

    # Create blank image for drawing.
    image1 = Image.new('RGB', (disp.width, disp.height), 0)
    draw = ImageDraw.Draw(image1)
    font = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 12)
    font1 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
    font2 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)

    logging.info ("***draw line")
    draw.line([(0,0),(127,0)], fill = "RED")
    draw.line([(0,0),(0,95)], fill = "RED")
    draw.line([(0,95),(127,95)], fill = "RED")
    draw.line([(127,0),(127,95)], fill = "RED")
    
    image1 = image1.rotate(0)
    disp.ShowImage(disp.getbuffer(image1))
    time.sleep(3)

    disp.clear()

except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    disp.module_exit()
    exit()