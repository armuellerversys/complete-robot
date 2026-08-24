import display_oled


print("Initializing OLED display...")
try:
    displayOledText = display_oled.DisplayOledText()
    print("Display initialized successfully.")
    displayOledText.init_display()
    displayOledText.draw_text_screen("Hello, OLED!", 16)
    print("Text displayed on OLED.")
finally:
    print("Closing OLED display...")
    displayOledText.close()
