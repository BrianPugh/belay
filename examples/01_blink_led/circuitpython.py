import argparse
import time

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

# Setup the connection with the micropython board.
# This also executes a few common imports on-device.
device = belay.Device(args.port)


@device.setup
def setup():  # The function name doesn't matter, but is "setup" by convention.
    import board
    import digitalio

    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT


# This sends the function's code over to the board.
# Calling the local ``set_led`` function will
# execute it on-device.
@device.task
def set_led(state):
    print(f"Printing from device; turning LED to {state}.")
    led.value = state

setup()

while True:
    set_led(True)
    time.sleep(0.5)
    set_led(False)
    time.sleep(0.5)
