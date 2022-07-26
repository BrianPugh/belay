import argparse
from time import sleep

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

device = belay.Device(args.port)

device.sync("board/")

print('Using synced "led.py" via explicit commands.')
device("import led")
for _ in range(3):
    device("led.set(25, True)")
    sleep(0.5)
    device("led.set(25, False)")
    sleep(0.5)


print('Using synced "led.py" via task decorator.')


@device.task
def set_led(pin, value):
    import led

    led.set(pin, value)


for _ in range(3):
    set_led(25, True)
    sleep(0.5)
    set_led(25, False)
    sleep(0.5)


print('Using synced "somemodule/led.py" via task decorator.')


@device.task
def set_somemodule_led(pin, value):
    import somemodule.led

    somemodule.led.set(pin, value)


for _ in range(3):
    set_somemodule_led(25, True)
    sleep(0.5)
    set_somemodule_led(25, False)
    sleep(0.5)


print("Reading a synced file via task decorator. Contents:")


@device.task
def read_file(fn):
    with open(fn, "r") as f:
        return f.read()


print(read_file("hello_world.txt"))
