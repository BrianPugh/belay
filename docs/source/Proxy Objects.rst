Proxy Objects
=============

:class:`~belay.ProxyObject` provides a way to interact with remote objects on your MicroPython or CircuitPython device as if they were local Python objects. This is useful for hardware peripherals, custom classes, or modules that cannot be serialized.

Overview
^^^^^^^^

When executing code with :meth:`~belay.Device.task` or :meth:`~belay.Device.__call__`, return values must typically be serializable literals (numbers, strings, lists, dicts, etc.). :class:`~belay.ProxyObject` creates a transparent wrapper for non-serializable objects, forwarding operations to the device automatically.

Creating Proxy Objects
^^^^^^^^^^^^^^^^^^^^^^^

Use :meth:`.Device.proxy` to create proxies:

.. code-block:: python

   from belay import Device

   device = Device("/dev/ttyUSB0")

   # Create and proxy a remote object
   device("sensor = TemperatureSensor()")
   sensor = device.proxy("sensor")
   temp = sensor.temperature
   sensor.calibrate()

   # Import modules directly
   machine = device.proxy("import machine")
   pin = machine.Pin(25, machine.Pin.OUT)
   pin.on()

Return Value Behavior
^^^^^^^^^^^^^^^^^^^^^^

Values are automatically returned directly or as proxies based on type:

- **Immutable types** (bool, int, float, str, bytes, none) → **returned directly**
- **Mutable types** (list, dict, custom objects) → **returned as** :class:`~belay.ProxyObject`

.. code-block:: python

   temp = sensor.temperature  # Returns float directly (e.g., 23.5)
   config = sensor.config  # Returns ProxyObject wrapping dict
   threshold = config["threshold"]  # Returns value directly

Working with Collections
^^^^^^^^^^^^^^^^^^^^^^^^^

Lists, dictionaries, and nested objects work transparently:

.. code-block:: python

   # Lists
   device("data = [1, 2, 3, 4, 5]")
   data = device.proxy("data")
   print(data[0], data[-1])  # 1 5
   data[0] = 100  # Modify remotely
   print(len(data))  # 5
   for item in data:  # Iterate
       print(item)

   # Dictionaries
   device("config = {'brightness': 10, 'mode': 'auto'}")
   config = device.proxy("config")
   brightness = config["brightness"]  # 10
   config["brightness"] = 20
   if "mode" in config:
       print("Mode configured")

Working with Methods and Modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Call methods and use modules naturally:

.. code-block:: python

   # Methods
   device(
       """
   class LED:
       def __init__(self, pin):
           self.state = False
       def on(self):
           self.state = True
   led = LED(25)
   """
   )
   led = device.proxy("led")
   led.on()
   print(led.state)  # True

   # Modules
   machine = device.proxy("import machine")
   led_pin = machine.Pin(25, machine.Pin.OUT)  # remotely creates an led_pin object
   led_pin.on()

Memory Management
^^^^^^^^^^^^^^^^^

Proxies automatically delete remote references when garbage collected. Use ``delete=False`` to prevent this:

.. code-block:: python

   # Auto-deletes micropython object when local object "temp" goes out-of-scope and garbage collected.
   temp = device.proxy("temp_obj").value

   # Never deletes micropython object
   machine = device.proxy("import machine", delete=False)
