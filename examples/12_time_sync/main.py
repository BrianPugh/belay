"""Time Synchronization Example

This example demonstrates how to synchronize time between the host computer
and a MicroPython/CircuitPython device, and how to use timestamp conversion
for accurate time-series data collection.
"""

import argparse
import datetime
import time

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

# Connect to device. Time synchronization happens automatically by default.
device = belay.Device(args.port)

print(f"  Device Time Offset: {device.time_offset:.6f} seconds")
print(f"  (Device time - Host time)")
print()

# Get current device time
device_time = device("__belay_monotonic()") / 1000  # seconds
print(f"Device monotonic time: {device_time} seconds.")

# Convert to host epoch time
host_time = device_time - device.time_offset
host_datetime = datetime.datetime.fromtimestamp(host_time)
print(f"Converted to host time: {host_time:.3f}")
print(f"Human-readable: {host_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
print()

print("=" * 60)
print("Time-Series Data Collection Example")
print("=" * 60)


# Setup sensor reading task (simulated with random data)
@device.setup
def setup_sensor():
    import random

    def read_sensor():
        """Simulate reading a sensor value."""
        return random.random() * 100  # Random value 0-100


if device.implementation.name == "circuitpython":

    @device.task
    def get_reading_with_timestamp():
        import supervisor

        return supervisor.ticks_ms(), read_sensor()

else:

    @device.task
    def get_reading_with_timestamp():
        import time

        return time.ticks_ms(), read_sensor()


setup_sensor()

print("Collecting 3 sensor readings with timestamps...")
print()
print(f"{'#':<4} {'Device Time':<15} {'Host Time':<30} {'Value':<10}")
print("-" * 70)

for i in range(3):
    device_timestamp, value = get_reading_with_timestamp()
    host_timestamp = (device_timestamp / 1000) - device.time_offset
    host_datetime = datetime.datetime.fromtimestamp(host_timestamp)

    print(
        f"{i+1:<4} "
        f"{device_timestamp:<15.3f} "
        f"{host_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]:<30} "
        f"{value:<10.2f}"
    )

    time.sleep(0.5)

device.close()
