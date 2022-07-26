import argparse

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

device = belay.Device(args.port)

device.sync("board/")

device(
    """
from pico_lcd_0_96 import LCD_0inch96
lcd = LCD_0inch96()
"""
)

# color is BGR
RED = 0x00F8
GREEN = 0xE007
BLUE = 0x1F00
WHITE = 0xFFFF
BLACK = 0x0000


@device.task
def display_text(text, x, y, text_color, bg_color):
    if bg_color is not None:
        lcd.fill(bg_color)
    lcd.text(text, x, y, text_color)
    lcd.display()


display_text("This is Belay!", 0, 15, WHITE, BLACK)
display_text("Belay makes it easy", 0, 30, RED, None)
display_text("to control hardware", 0, 45, GREEN, None)
display_text("from a python script.", 0, 60, BLUE, None)
