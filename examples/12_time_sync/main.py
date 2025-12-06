"""Time Synchronization Example

This example demonstrates how to synchronize time between the host computer
and a MicroPython/CircuitPython device, and how to use the return_time feature
for accurate time-series data collection.
"""

import argparse
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

# ============================================================================
# Method 1: Using return_time=True (Recommended)
# ============================================================================
print("=" * 60)
print("Method 1: Using return_time=True (Recommended)")
print("=" * 60)


# Setup sensor reading task (simulated with random data)
@device.setup
def setup_sensor():
    import random

    def read_sensor():
        """Simulate reading a sensor value."""
        return random.random() * 100  # Random value 0-100


setup_sensor()


# The return_time=True parameter automatically includes timestamps
@device.task(return_time=True)
def get_reading():
    return read_sensor()


print("Collecting 3 sensor readings with automatic timestamps...")
print()
print(f"{'#':<4} {'Host Timestamp':<30} {'Value':<10}")
print("-" * 50)

for i in range(3):
    # Returns (value, datetime) tuple automatically!
    value, timestamp = get_reading()

    print(f"{i+1:<4} " f"{timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]:<30} " f"{value:<10.2f}")

    time.sleep(1)

print()

# ============================================================================
# Method 2: Manual timestamp conversion (for buffered data)
# ============================================================================
print("=" * 60)
print("Method 2: Manual Conversion (for buffered data)")
print("=" * 60)


# Use this approach when data is buffered on-device and returned later
@device.task
def get_buffered_readings(count):
    """Collect multiple readings with device timestamps."""
    import time

    readings = []
    for _ in range(count):
        timestamp_ms = time.ticks_ms()
        value = read_sensor()
        readings.append((timestamp_ms, value))
        time.sleep_ms(1000)
    return readings


print("Collecting 3 buffered readings...")
print()
print(f"{'#':<4} {'Device ms':<15} {'Host Timestamp':<30} {'Value':<10}")
print("-" * 65)

readings = get_buffered_readings(3)
for i, (device_ms, value) in enumerate(readings):
    # Convert device timestamp to host time using the offset
    from datetime import datetime

    host_time_sec = (device_ms / 1000.0) - device.time_offset
    host_timestamp = datetime.fromtimestamp(host_time_sec)

    print(
        f"{i+1:<4} "
        f"{device_ms:<15} "
        f"{host_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]:<30} "
        f"{value:<10.2f}"
    )

print()

# ============================================================================
# Method 3: Generator with return_time=True
# ============================================================================
print("=" * 60)
print("Method 3: Generator with return_time=True")
print("=" * 60)


@device.task(return_time=True)
def stream_readings(count):
    """Stream readings with automatic timestamps."""
    import time

    for _ in range(count):
        yield read_sensor()
        time.sleep_ms(1000)


print("Streaming 3 readings...")
print()
print(f"{'#':<4} {'Host Timestamp':<30} {'Value':<10}")
print("-" * 50)

for i, (value, timestamp) in enumerate(stream_readings(3)):
    print(f"{i+1:<4} " f"{timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]:<30} " f"{value:<10.2f}")

device.close()
