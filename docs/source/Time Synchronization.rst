Time Synchronization
====================

Belay includes an automatic time synchronization feature that aligns the device's internal timer with the host computer's clock.
This enables fairly accurate timestamping of events on the device relative to host time, which may be important for data logging, sensor fusion, and coordinating multiple devices.

How It Works
------------

When time synchronization is enabled (the default), Belay periodically synchronizes the device's ``time.ticks_ms()`` timer with the host computer's clock.
This synchronization happens automatically:

1. **On connection** - Initial sync when ``Device`` is created
2. **Periodically during execution** - Maintains alignment over time
3. **Per remote call** - Small sync overhead (~1.3ms) on each device communication

The synchronization uses a simple offset calculation:

.. code-block:: python

   device_time_ms = time.ticks_ms()  # On device
   host_time_s = time.time()  # On host
   offset = host_time_s - (device_time_ms / 1000.0)

This offset is stored and used to convert device timestamps to host time.

Enabling and Disabling
----------------------

Time synchronization is **enabled by default**. You can disable it when creating a ``Device``:

.. code-block:: python

   import belay

   # With time synchronization (default)
   device = belay.Device("/dev/ttyUSB0")

   # Without time synchronization
   device = belay.Device("/dev/ttyUSB0", auto_sync_time=False)

You can also disable it for the CLI ``latency`` command:

.. code-block:: bash

   # With time synchronization (default)
   belay latency /dev/ttyUSB0

   # Without time synchronization
   belay latency /dev/ttyUSB0 --without-timing

Performance Impact
------------------

Time synchronization adds approximately **1.3 ms** of overhead per round-trip communication.
This overhead is negligible for most applications.

Benchmark results on an M3 MacBook Pro with an RP2040 device over USB:

.. code-block:: text

   # With time synchronization (default)
   Average latency: 5.45 ms

   # Without time synchronization
   Average latency: 4.19 ms

For most applications, the benefits of automatic time synchronization outweigh the small performance cost.

Use Cases
---------

Time synchronization is particularly useful for:

* **Data logging** - Timestamp sensor readings with host time
* **Multi-device coordination** - Synchronize events across multiple devices
* **Sensor fusion** - Combine data from device sensors with host-side processing
* **Debugging** - Correlate device events with host-side logs
* **Real-time analysis** - Stream timestamped data for live visualization

Example: Automatic Time Conversion
-----------------------------------

With time synchronization enabled, you can easily convert device timestamps to host time:

.. code-block:: python

   import belay
   import time

   device = belay.Device("/dev/ttyUSB0")  # auto_sync_time=True by default


   @device.task
   def read_sensor_with_time():
       """Read sensor and return value with device timestamp."""
       sensor_value = ADC(26).read_u16()  # Read analog sensor
       timestamp_ms = time.ticks_ms()
       return sensor_value, timestamp_ms


   # Read sensor
   value, device_time_ms = read_sensor_with_time()

   # Convert device time to host time
   host_time = device.device_time_to_host(device_time_ms)

   print(f"Sensor reading: {value} at {time.ctime(host_time)}")

Example: Manual Time Conversion
--------------------------------

For more control, you can manually handle time conversion without using the automatic synchronization:

.. code-block:: python

   import belay
   import time

   device = belay.Device("/dev/ttyUSB0", auto_sync_time=False)


   @device.task
   def read_sensor_with_time():
       """Read sensor and return value with device timestamp."""
       sensor_value = ADC(26).read_u16()
       timestamp_ms = time.ticks_ms()
       return sensor_value, timestamp_ms


   # Establish time offset manually
   device_time_ms = device("time.ticks_ms()")
   host_time_before = time.time()
   offset = host_time_before - (device_time_ms / 1000.0)


   # Read sensor
   value, device_time_ms = read_sensor_with_time()

   # Manually convert device time to host time
   host_time = offset + (device_time_ms / 1000.0)

   print(f"Sensor reading: {value} at {time.ctime(host_time)}")

This approach gives you full control over when and how time synchronization occurs,
which can be useful for minimizing communication overhead in time-critical applications.

Example: High-Frequency Data Logging
-------------------------------------

For high-frequency data logging, you can batch readings on the device and convert timestamps later:

.. code-block:: python

   import belay
   import time

   device = belay.Device("/dev/ttyUSB0")


   @device.setup
   def setup_logging():
       # Preallocate arrays for fast logging
       max_samples = 1000
       sensor_values = bytearray(max_samples * 2)  # 2 bytes per reading
       timestamps = bytearray(max_samples * 4)  # 4 bytes per timestamp
       sample_count = 0


   @device.task
   def collect_data(num_samples, interval_ms):
       """Collect sensor data at high frequency."""
       global sample_count
       sample_count = 0

       for i in range(num_samples):
           # Read sensor
           value = ADC(26).read_u16()

           # Store value (16-bit)
           sensor_values[i * 2] = value & 0xFF
           sensor_values[i * 2 + 1] = (value >> 8) & 0xFF

           # Store timestamp (32-bit)
           timestamp = time.ticks_ms()
           timestamps[i * 4] = timestamp & 0xFF
           timestamps[i * 4 + 1] = (timestamp >> 8) & 0xFF
           timestamps[i * 4 + 2] = (timestamp >> 16) & 0xFF
           timestamps[i * 4 + 3] = (timestamp >> 24) & 0xFF

           sample_count += 1
           time.sleep_ms(interval_ms)

       return sample_count


   @device.task
   def get_data():
       """Retrieve collected data."""
       # Convert to lists for transmission
       values = []
       times = []

       for i in range(sample_count):
           # Reconstruct 16-bit value
           value = sensor_values[i * 2] | (sensor_values[i * 2 + 1] << 8)
           values.append(value)

           # Reconstruct 32-bit timestamp
           timestamp = (
               timestamps[i * 4]
               | (timestamps[i * 4 + 1] << 8)
               | (timestamps[i * 4 + 2] << 16)
               | (timestamps[i * 4 + 3] << 24)
           )
           times.append(timestamp)

       return values, times


   # Initialize
   setup_logging()

   # Collect 100 samples at 10ms intervals
   num_samples = collect_data(100, 10)
   print(f"Collected {num_samples} samples")

   # Retrieve data
   values, device_times = get_data()

   # Convert all timestamps to host time
   host_times = [device.device_time_to_host(t) for t in device_times]

   # Process data
   for value, host_time in zip(values, host_times):
       print(f"{time.ctime(host_time)}: {value}")

This approach minimizes communication overhead during data collection while still maintaining accurate timestamps.

API Reference
-------------

Device Methods
^^^^^^^^^^^^^^

``device.device_time_to_host(device_time_ms)``
    Convert a device timestamp (from ``time.ticks_ms()``) to host time (Unix timestamp).

    **Parameters:**
        * ``device_time_ms`` (int) - Device time in milliseconds from ``time.ticks_ms()``

    **Returns:**
        * float - Host time as Unix timestamp (seconds since epoch)

    **Example:**

    .. code-block:: python

        device_time = device("time.ticks_ms()")
        host_time = device.device_time_to_host(device_time)
        print(f"Device time {device_time}ms = {time.ctime(host_time)}")

Device Constructor Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``auto_sync_time`` (bool, default=True)
    Enable automatic time synchronization between device and host.
    When enabled, adds approximately 1.3ms overhead per round-trip communication.

    **Example:**

    .. code-block:: python

        # Enable automatic time sync (default)
        device = belay.Device("/dev/ttyUSB0", auto_sync_time=True)

        # Disable automatic time sync
        device = belay.Device("/dev/ttyUSB0", auto_sync_time=False)

Best Practices
--------------

1. **Use automatic sync for most applications** - The 1.3ms overhead is negligible for most use cases
2. **Disable sync for ultra-low latency** - Only disable if you need the absolute lowest latency
3. **Batch timestamps on device** - For high-frequency logging, store timestamps on-device and convert them in bulk
4. **Handle timer wraparound** - ``time.ticks_ms()`` wraps around every ~49 days; use ``time.ticks_diff()`` for interval calculations
5. **Test with actual workload** - Measure performance with your specific application to determine if disabling sync is necessary

Troubleshooting
---------------

**Q: My timestamps seem incorrect**

A: Ensure time synchronization is enabled (``auto_sync_time=True``). Check that your device's timer hasn't wrapped around (occurs every ~49 days).

**Q: Can I sync time manually?**

A: Yes, you can disable automatic sync and establish the offset manually as shown in the "Manual Time Conversion" example.

**Q: Does time sync work with multiple devices?**

A: Yes, each ``Device`` instance maintains its own time synchronization. All devices can be synchronized to the same host clock.

**Q: What if my device doesn't have a real-time clock (RTC)?**

A: Time synchronization uses the device's ``time.ticks_ms()`` timer, which is available on all MicroPython devices. No RTC is required.
