import argparse
from time import sleep

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="ws://192.168.1.100")
parser.add_argument("--password", default="python")
args = parser.parse_args()

print("Connecting to device")
device = belay.Device(args.port, password=args.password)

print("Syncing filesystem.")
# Sync our WiFi information and WebREPL configuration.
device.sync("board/")


print("Sending set_led task")


@device.task
def set_led(counter, state):
    # Configuration for a Pi Pico board.
    Pin(25, Pin.OUT).value(state)
    return counter


for counter in range(10_000):
    print("led on  ", end="")
    res = set_led(counter, True)
    print(f"Counter: {res}", end="\r")
    sleep(0.5)

    print("led off ", end="")
    res = set_led(counter, False)
    print(f"Counter: {res}", end="\r")
    sleep(0.5)
