import argparse
from time import sleep

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

device = belay.Device(args.port)


@device.task
def read_temperature() -> float:
    # ADC4 is attached to an internal temperature sensor
    sensor_temp = ADC(4)
    reading = sensor_temp.read_u16()
    reading *= 3.3 / 65535  # Convert reading to a voltage.
    temperature = 27 - (reading - 0.706) / 0.001721  # Convert voltage to Celsius
    return temperature


while True:
    temperature = read_temperature()
    print(f"Temperature: {temperature:.1f}C")
    sleep(0.5)
