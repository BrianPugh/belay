import argparse
import time

from belay import Device

parser = argparse.ArgumentParser()
parser.add_argument("--device1", default="/dev/ttyUSB0")
parser.add_argument("--device2", default="/dev/ttyUSB1")
args = parser.parse_args()


class MyDevice(Device):
    @Device.task
    def set_led(state):
        Pin(25, Pin.OUT).value(state)


device1 = MyDevice(args.device1)
device2 = MyDevice(args.device2)

while True:
    device1.set_led(True)
    device2.set_led(False)
    time.sleep(0.5)
    device1.set_led(False)
    device2.set_led(True)
    time.sleep(0.5)
