import argparse
from time import sleep

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

device = belay.Device(args.port)


@device.task
def read_temperature():
    return microcontroller.cpu.temperature


while True:
    temperature = read_temperature()
    print(f"Temperature: {temperature:.1f}C")
    sleep(0.5)
