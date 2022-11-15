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
        Pin(25, Pin.OUT).value(i % 2)
        yield i
        if i >= 10:
            break
        i += 1


@device.task
def communicate(x):
    new_val = yield "Device: " + str(x)
    print(new_val)
    new_val = yield "Device: " + str(new_val)
    new_val = yield "Device: " + str(new_val)


for index in count():
    time.sleep(0.5)
    print(index)

# Demonstrate the generator send command
generator = communicate("foo")
print(generator.send(None))
print(generator.send("bar"))
print(generator.send("baz"))
