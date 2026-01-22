import ledshim

class Leds: 

    green = (0,255, 0)
    orange = (255, 128, 0)
    red = (255, 0, 0)
    blue = (0, 0, 255)
    pink = (255, 182, 193)
    purple = (157, 0, 255)
    yellow = (255, 128, 0)
    white = (255, 255, 255)

    @property
    def count(self):
        return ledshim.width

    def set_one(self, led_number, color):
        ledshim.set_pixel(led_number, *color)

    def set_range(self, led_range, color):
        for pixel in led_range:
            ledshim.set_pixel(pixel, *color)

    def set_all(self, color):
        ledshim.set_all(*color)

    def clear(self):
        ledshim.clear()
        self.show()

    def show(self):
        ledshim.show()

    def showWhite(self):
        self.set_all(self.white)
        self.show()

    def showBlue(self):
        self.set_all(self.blue)
        self.show()

    def showRed(self):
        self.set_all(self.red)
        self.show()

    def showGreen(self):
        self.set_all(self.green)
        self.show()

    def showYellow(self):
        self.set_all(self.yellow)
        self.show()

    def showPurple(self):
        self.set_all(self.purple)
        self.show()

    def showPink(self):
        self.set_all(self.pink)
        self.show()

    def showOrange(self):
        self.set_all(self.orange)
        self.show()

    @staticmethod
    def set_led_orange():
        ledshim.set_all(255, 165, 0)
        ledshim.show()

    @staticmethod
    def set_led_white():
        ledshim.set_all(255, 255, 255)
        ledshim.show()

    @staticmethod
    def set_green_one():
        ledshim.set_pixel(1, 0, 255, 0)
        ledshim.show()

