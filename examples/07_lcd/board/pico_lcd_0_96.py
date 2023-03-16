import time

import framebuf
from machine import PWM, SPI, Pin

# color is BGR
RED = 0x00F8
GREEN = 0xE007
BLUE = 0x1F00
WHITE = 0xFFFF
BLACK = 0x0000


class LCD_0inch96(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 160
        self.height = 80

        self.cs = Pin(9, Pin.OUT)
        self.rst = Pin(12, Pin.OUT)
        #        self.bl = Pin(13,Pin.OUT)
        self.cs(1)
        # pwm = PWM(Pin(13))#BL
        # pwm.freq(1000)
        self.spi = SPI(1)
        self.spi = SPI(1, 1000_000)
        self.spi = SPI(
            1, 10000_000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=None
        )
        self.dc = Pin(8, Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.Init()
        self.SetWindows(0, 0, self.width - 1, self.height - 1)

    def reset(self):
        self.rst(1)
        time.sleep(0.2)
        self.rst(0)
        time.sleep(0.2)
        self.rst(1)
        time.sleep(0.2)

    def write_cmd(self, cmd):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))

    def write_data(self, buf):
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def backlight(self, value):  # value:  min:0  max:1000
        pwm = PWM(Pin(13))  # BL
        pwm.freq(1000)
        if value >= 1000:
            value = 1000
        data = int(value * 65536 / 1000)
        pwm.duty_u16(data)

    def Init(self):
        self.reset()
        self.backlight(10000)

        self.write_cmd(0x11)
        time.sleep(0.12)
        self.write_cmd(0x21)
        self.write_cmd(0x21)

        self.write_cmd(0xB1)
        self.write_data(0x05)
        self.write_data(0x3A)
        self.write_data(0x3A)

        self.write_cmd(0xB2)
        self.write_data(0x05)
        self.write_data(0x3A)
        self.write_data(0x3A)

        self.write_cmd(0xB3)
        self.write_data(0x05)
        self.write_data(0x3A)
        self.write_data(0x3A)
        self.write_data(0x05)
        self.write_data(0x3A)
        self.write_data(0x3A)

        self.write_cmd(0xB4)
        self.write_data(0x03)

        self.write_cmd(0xC0)
        self.write_data(0x62)
        self.write_data(0x02)
        self.write_data(0x04)

        self.write_cmd(0xC1)
        self.write_data(0xC0)

        self.write_cmd(0xC2)
        self.write_data(0x0D)
        self.write_data(0x00)

        self.write_cmd(0xC3)
        self.write_data(0x8D)
        self.write_data(0x6A)

        self.write_cmd(0xC4)
        self.write_data(0x8D)
        self.write_data(0xEE)

        self.write_cmd(0xC5)
        self.write_data(0x0E)

        self.write_cmd(0xE0)
        self.write_data(0x10)
        self.write_data(0x0E)
        self.write_data(0x02)
        self.write_data(0x03)
        self.write_data(0x0E)
        self.write_data(0x07)
        self.write_data(0x02)
        self.write_data(0x07)
        self.write_data(0x0A)
        self.write_data(0x12)
        self.write_data(0x27)
        self.write_data(0x37)
        self.write_data(0x00)
        self.write_data(0x0D)
        self.write_data(0x0E)
        self.write_data(0x10)

        self.write_cmd(0xE1)
        self.write_data(0x10)
        self.write_data(0x0E)
        self.write_data(0x03)
        self.write_data(0x03)
        self.write_data(0x0F)
        self.write_data(0x06)
        self.write_data(0x02)
        self.write_data(0x08)
        self.write_data(0x0A)
        self.write_data(0x13)
        self.write_data(0x26)
        self.write_data(0x36)
        self.write_data(0x00)
        self.write_data(0x0D)
        self.write_data(0x0E)
        self.write_data(0x10)

        self.write_cmd(0x3A)
        self.write_data(0x05)

        self.write_cmd(0x36)
        self.write_data(0xA8)

        self.write_cmd(0x29)

    def SetWindows(self, Xstart, Ystart, Xend, Yend):  # example max:0,0,159,79
        Xstart = Xstart + 1
        Xend = Xend + 1
        Ystart = Ystart + 26
        Yend = Yend + 26
        self.write_cmd(0x2A)
        self.write_data(0x00)
        self.write_data(Xstart)
        self.write_data(0x00)
        self.write_data(Xend)

        self.write_cmd(0x2B)
        self.write_data(0x00)
        self.write_data(Ystart)
        self.write_data(0x00)
        self.write_data(Yend)

        self.write_cmd(0x2C)

    def display(self):
        self.SetWindows(0, 0, self.width - 1, self.height - 1)
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)


if __name__ == "__main__":
    lcd = LCD_0inch96()
    lcd.fill(BLACK)
    lcd.text("Hello pico!", 35, 15, GREEN)
    lcd.text("This is:", 50, 35, GREEN)
    lcd.text("Pico-LCD-0.96", 30, 55, GREEN)
    lcd.display()

    lcd.hline(10, 10, 140, BLUE)
    lcd.hline(10, 70, 140, BLUE)
    lcd.vline(10, 10, 60, BLUE)
    lcd.vline(150, 10, 60, BLUE)

    lcd.hline(0, 0, 160, BLUE)
    lcd.hline(0, 79, 160, BLUE)
    lcd.vline(0, 0, 80, BLUE)
    lcd.vline(159, 0, 80, BLUE)

    lcd.display()
    time.sleep(3)
    # game GUI
    ###
    lcd.fill(WHITE)

    i = 0
    while i <= 80:
        lcd.hline(0, i, 160, BLACK)
        i = i + 10
    i = 0
    while i <= 160:
        lcd.vline(i, 0, 80, BLACK)
        i = i + 10
    lcd.display()
    ###

    x = 80
    y = 40
    color = RED
    colorflag = 0

    KEY_UP = Pin(2, Pin.IN, Pin.PULL_UP)
    KEY_DOWN = Pin(18, Pin.IN, Pin.PULL_UP)
    KEY_LEFT = Pin(16, Pin.IN, Pin.PULL_UP)
    KEY_RIGHT = Pin(20, Pin.IN, Pin.PULL_UP)
    KEY_CTRL = Pin(3, Pin.IN, Pin.PULL_UP)
    KEY_A = Pin(15, Pin.IN, Pin.PULL_UP)
    KEY_B = Pin(17, Pin.IN, Pin.PULL_UP)

    while 1:
        key_flag = 1
        if key_flag and (
            KEY_UP.value() == 0
            or KEY_DOWN.value() == 0
            or KEY_LEFT.value() == 0
            or KEY_RIGHT.value() == 0
            or KEY_CTRL.value() == 0
            or KEY_A.value() == 0
            or KEY_B.value() == 0
        ):
            time.sleep(0.05)
            key_flag = 0
            m = x
            n = y
            ###go up
            if KEY_UP.value() == 0:
                y = y - 10
                if y < 0:
                    y = 70
            if KEY_DOWN.value() == 0:
                y = y + 10
                if y >= 80:
                    y = 0
            if KEY_LEFT.value() == 0:
                x = x - 10
                if x < 0:
                    x = 150
            if KEY_RIGHT.value() == 0:
                x = x + 10
                if x >= 160:
                    x = 0
            if KEY_CTRL.value() == 0:
                colorflag += 1
                if colorflag == 1:
                    color = RED
                elif colorflag == 2:
                    color = GREEN
                elif colorflag == 3:
                    color = BLUE
                    colorflag = 0

            lcd.fill_rect(m, n, 10, 10, WHITE)
            lcd.hline(m, n, 10, BLACK)
            lcd.hline(m, n + 10, 10, BLACK)
            lcd.vline(m, n, 10, BLACK)
            lcd.vline(m + 10, n, 10, BLACK)

            lcd.rect(x + 1, y + 1, 9, 9, color)

            if KEY_A.value() == 0:
                lcd.fill_rect(x + 1, y + 1, 9, 9, color)
                lcd.fill_rect(m + 1, n + 1, 9, 9, color)

            if KEY_B.value() == 0:
                lcd.fill(WHITE)
                i = 0
                while i <= 80:
                    lcd.hline(0, i, 160, BLACK)
                    i = i + 10
                i = 0
                while i <= 160:
                    lcd.vline(i, 0, 80, BLACK)
                    i = i + 10

        lcd.display()

    time.sleep(1)
