import argparse
from time import sleep

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

device = belay.Device(args.port)

print("")
print("*******************************************************")
print("This example does not work. It will raise an exception.")
print("*******************************************************")
print("")


@device.thread
def run_led_loop(period):
    pass
