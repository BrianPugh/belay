Time Synchronization
====================

Belay includes an automatic time synchronization feature that aligns the device's internal timer with the host computer's clock.
This enables fairly accurate timestamping of events on the device relative to host time.

When to Use Time Synchronization
---------------------------------

For most applications, **host-side timestamps are simpler and sufficient**:

.. code-block:: python

   import time
   import belay

   device = belay.Device("/dev/ttyUSB0", auto_sync_time=False)


   @device.task
   def read_sensor():
       return sensor.read()


   # Simple approach - timestamp on the host when data arrives
   value = read_sensor()
   timestamp = time.time()  # Accurate enough for most use cases

Only use Belay's time-sync feature if you need:

* High time accuracy (< 5ms) between device events and timestamps
* Timestamps for data collected and buffered on-device
* Precise correlation between multiple devices

Testing Your Connection Latency
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the ``belay latency`` CLI command to measure your device/connection round-trip time:

.. code-block:: bash

   belay latency /dev/ttyUSB0

If your measured latency is acceptable for your application (e.g., 10-50ms for USB),
host-side timestamps are the simpler choice with zero overhead.

How It Works
------------

When time synchronization is enabled (the default), Belay periodically synchronizes the device's ``time.ticks_ms()`` timer with the host computer's clock.
This synchronization happens automatically on device creation, and piggybacks on every device communication.

The synchronization uses a simple offset calculation:

.. code-block:: python

   device_time_ms = time.ticks_ms()  # On device time in milliseconds
   host_time_s = time.time()  # On host time in seconds
   offset = host_time_s - (device_time_ms / 1000.0)

This offset is stored and used to convert device timestamps to host time:

.. code-block:: python

   device_time_ms = device("time.ticks_ms()")
   host_time = (device_time_ms / 1000.0) - device.time_offset
   print(f"Device event occurred at: {time.ctime(host_time)}")

Using return_time with Tasks
----------------------------

The simplest way to get accurate timestamps for task results is using the ``return_time`` parameter on ``@device.task``:

.. code-block:: python

   import belay

   device = belay.Device("/dev/ttyUSB0")


   @device.task(return_time=True)
   def read_sensor():
       return sensor.read()


   # Returns (value, datetime) tuple
   value, timestamp = read_sensor()
   print(f"Sensor reading: {value} at {timestamp}")

When ``return_time=True``, the task returns a tuple of ``(result, datetime.datetime)`` where the datetime represents the **estimated midpoint time** when the task executed on the device, converted to host time.

The timestamp is captured by measuring **device time** immediately before and after evaluating the expression, then averaging the two. This device-time is then converted to host-time using the time-offset-synchronization. This provides a good estimate of when the actual computation occurred, accounting for any time spent in the operation itself.

This also works with generator tasks - each yielded value becomes a ``(value, datetime)`` tuple:

.. code-block:: python

   @device.task(return_time=True)
   def stream_readings(count):
       for _ in range(count):
           yield sensor.read()


   for value, timestamp in stream_readings(10):
       print(f"{timestamp}: {value}")

You can also use ``return_time`` directly with ``device()`` calls:

.. code-block:: python

   # Get a value with its timestamp
   result, timestamp = device("sensor.read()", return_time=True)

If time synchronization is not available (e.g., ``auto_sync_time=False`` and no manual ``sync_time()`` call), using ``return_time=True`` will raise a ``ValueError``.

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

The only pragmatic downside to the default `auto_sync_time=True` is that it can slow down initial startup by a few dozen milliseconds.

Example
-------

For a complete working example with code samples and detailed usage patterns, see `Example 12: Time Synchronization <https://github.com/BrianPugh/belay/tree/main/examples/12_time_sync>`_.
