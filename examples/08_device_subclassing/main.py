import argparse
import time

from belay import Device

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()


class MyDevice(Device):
    # NOTE: ``Device`` is capatalized here!
    @Device.task
    def set_led(state):
        Pin(25, Pin.OUT).value(state)

    @Device.task
    def read_temperature():
        # ADC4 is attached to an internal temperature sensor
        sensor_temp = ADC(4)
        reading = sensor_temp.read_u16()
        reading *= 3.3 / 65535  # Convert reading to a voltage.
        temperature = 27 - (reading - 0.706) / 0.001721  # Convert voltage to Celsius
        return temperature


device = MyDevice(args.port)

while True:
    device.set_led(True)
    temperature = device.read_temperature()
    print(f"Temperature: {temperature:.1f}C")
    time.sleep(0.5)
    device.set_led(False)
    time.sleep(0.5)
