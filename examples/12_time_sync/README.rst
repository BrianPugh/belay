Example 12: Time Synchronization
=================================

This example demonstrates Belay's time synchronization feature.
Also demonstrates using ``return_time=True`` with tasks.

Do You Actually Need Time Synchronization?
-------------------------------------------

For most applications, it's **simpler to just use host-side timestamps** instead of
synchronizing device time. Simply record the current host time when you receive data
from the device:

.. code-block:: python

   import time

   value = device_task()  # Get data from device
   timestamp = time.time()  # Host timestamp - simple!

This approach is accurate enough for most use cases and has zero overhead.

Only use Belay's time-sync feature if:

* You need high time accuracy (< 5ms between device event and timestamp)
* You're collecting data on-device and need timestamps for events that occurred in the past
* You need to correlate precise timing between multiple devices

Test Your Connection Latency First
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the ``belay latency`` command to measure your device/connection round-trip time:

.. code-block:: bash

   belay latency /dev/ttyUSB0

If the latency is acceptable for your application (e.g., > 5ms), host-side
timestamps are the simpler choice.

The return_time Parameter
-------------------------

The simplest way to get timestamps for task results is using ``return_time=True``:

.. code-block:: python

   @device.task(return_time=True)
   def read_sensor():
       return sensor.read()


   # Returns (value, datetime) tuple automatically
   value, timestamp = read_sensor()

This also works with generator tasks - each yielded value becomes a ``(value, datetime)`` tuple.

Running This Example
--------------------

To run this demo:

.. code-block:: bash

   python main.py --port YOUR_DEVICE_PORT_HERE

For example:

.. code-block:: bash

   python main.py --port /dev/ttyUSB0
