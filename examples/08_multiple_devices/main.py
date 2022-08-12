import argparse
import time

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--device1", default="/dev/ttyUSB0")
parser.add_argument("--device2", default="/dev/ttyUSB1")
args = parser.parse_args()

device1 = belay.Device(args.device1)
device2 = belay.Device(args.device2)


@device2.task
@device1.task
def set_led(state):
    # Configuration for a Pi Pico board.
    Pin(25, Pin.OUT).value(state)


# This will execute devices in order.
# Decorators start from the bottom and work their way upward.
# So device1 will execute, and upon completion, then device2 will execute.
print("Execute on all devices via decorated function.")
for _ in range(5):
    set_led(True)
    time.sleep(0.5)
    set_led(False)
    time.sleep(0.5)


print("Explicitly specify tasks per-device.")
for _ in range(5):
    device1.task.set_led(True)
    device2.task.set_led(False)

    time.sleep(0.5)

    device1.task.set_led(False)
    device2.task.set_led(True)

    time.sleep(0.5)


print("Reading temperature from devices.")


@device2.task
@device1.task
def read_temperature():
    # ADC4 is attached to an internal temperature sensor
    sensor_temp = ADC(4)
    reading = sensor_temp.read_u16()
    reading *= 3.3 / 65535  # Convert reading to a voltage.
    temperature = 27 - (reading - 0.706) / 0.001721  # Convert voltage to Celsius
    return temperature


for _ in range(5):
    device1_temp, device2_temp = read_temperature()
    print(f"{device1_temp=:.1f}    {device2_temp=:.1f}")
    time.sleep(0.5)


print("Starting blinking thread on all devices.")


@device2.thread
@device1.thread
def blink_thread():
    while True:
        set_led(True)
        time.sleep(0.5)
        set_led(False)
        time.sleep(0.5)


blink_thread()
