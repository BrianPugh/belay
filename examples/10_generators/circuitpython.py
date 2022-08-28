import argparse
import time

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

device = belay.Device(args.port)


@device.task
def count():
    i = 0
    while True:
        yield i
        if i >= 10:
            break
        i += 1


for index in count():
    time.sleep(0.5)
    print(index)
