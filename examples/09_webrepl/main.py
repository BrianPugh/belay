import argparse
from time import sleep

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

device = belay.Device(args.port)

# Sync our WiFi information and WebREPL configuration.
device.sync("board/")


@device.task
def set_led(state):
    # Configuration for a Pi Pico board.
    Pin(25, Pin.OUT).value(state)


while True:
    set_led(True)
    sleep(0.5)
    set_led(False)
    sleep(0.5)
