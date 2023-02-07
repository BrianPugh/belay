import argparse
import time

from belay import Device
from mydevice import MyDevice

parser = argparse.ArgumentParser()
parser.add_argument("--device1", default="/dev/ttyUSB0")
parser.add_argument("--device2", default="/dev/ttyUSB1")
args = parser.parse_args()


device1 = MyDevice(args.device1)
device2 = MyDevice(args.device2)

while True:
    device1.set_led(True)
    device2.set_led(False)
    temperature = device1.read_temperature()
    print(f"Temperature 1: {temperature:.1f}C")

    time.sleep(0.5)
    device1.set_led(False)
    device2.set_led(True)
    temperature = device2.read_temperature()
    print(f"Temperature 2: {temperature:.1f}C")
    time.sleep(0.5)
