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
