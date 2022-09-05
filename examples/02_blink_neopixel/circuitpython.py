import argparse
import time

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

# Setup the connection with the micropython board.
# This also executes a few common imports on-device.
device = belay.Device(args.port)

# Executes string on-device in a global context.
device("from neopixel_write import neopixel_write")
# Configuration for a RP2040-ZERO board.
device("pin = digitalio.DigitalInOut(board.GP16)")
device("pin.direction = digitalio.Direction.OUTPUT")


# This sends the function's code over to the board.
# Calling the local ``set_neopixel`` function will
# execute it on-device.
@device.task
def set_neopixel(r, g, b):
    neopixel_write(pin, bytearray([r, g, b]))


while True:
    set_neopixel(255, 0, 0)
    time.sleep(0.5)
    set_neopixel(0, 255, 0)
    time.sleep(0.5)
    set_neopixel(0, 0, 255)
    time.sleep(0.5)
