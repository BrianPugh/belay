import argparse
import time

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--device1", default="/dev/ttyUSB0")
parser.add_argument("--device2", default="/dev/ttyUSB1")
args = parser.parse_args()

device1 = belay.Device(args.device1)
device2 = belay.Device(args.device2)


# This sends the function's code over to the board.
# Calling the local ``set_led`` function will
# execute it on-device.
@device1.task
@device2.task
def set_led(state):
    # Configuration for a Pi Pico board.
    Pin(25, Pin.OUT).value(state)


print("Execute on all devices via decorated function.")
for _ in range(5):
    set_led(True)
    time.sleep(0.5)
    set_led(False)
    time.sleep(0.5)

print("Explicitly specify tasks per-device.")
for _ in range(5):
    device1.task.set_led(True)
    device2.task.set_led(False)

    time.sleep(0.5)

    device1.task.set_led(False)
    device2.task.set_led(True)

    time.sleep(0.5)
