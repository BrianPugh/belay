import argparse
import time

from belay import Device

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()


class MyDevice(Device):
    @Device.task
    def set_led(state):
        Pin(25, Pin.OUT).value(state)


device = MyDevice(args.port)

while True:
    my_device.set_led(True)
    time.sleep(0.5)
    my_device.set_led(False)
    time.sleep(0.5)
