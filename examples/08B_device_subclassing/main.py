import argparse
import time

from mydevice import MyDevice

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()


device = MyDevice(args.port)

while True:
    device.set_led(True)
    temperature = device.read_temperature()
    print(f"Temperature: {temperature:.1f}C")
    time.sleep(0.5)
    device.set_led(False)
    time.sleep(0.5)
