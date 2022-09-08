Connections
===========

This section describes the connection with the device, as well as other elements
regarding the connection of the device.


Reconnect
---------
In the event that the device is temporarily disconnected, Belay can re-attempt to
connect to the device and restore state. Typically, this will only work with projects
that are purely sensor/actuator IO and do not have complicated internal states.

To enable this feature, set the keyword ``attempts`` when declaring your ``Device``.
Belay will attempt up to ``attempts`` times to reconnect to the device with
1 second delay in-between attempts. If Belay cannot restore the connection, it will raise
a ``ConnectionLost`` exception.

Example:

.. code-block:: python

   device = Device("/dev/ttyUSB0", attempts=10)

By default, ``attempts=0``, meaning that Belay will **not** attempt to reconnect with the device.
If ``attempts`` is set to a negative value, Belay will infinitely attempt to reconnect with the device.
If using a serial connection, a serial device __might__ not be assigned to the name upon reconnecting.
See the `UDev Rules`_ section for ways to ensure the same name is assigned upon reconnection.


How State is Restored
^^^^^^^^^^^^^^^^^^^^^
This section describes how the state is restored on-device, so the user can understand
the limitations of Belay's reconnect feature.

1. When Belay sends a command to the device, the command is recorded into a command history.
   Function/generator calls **are not** recorded.
   These calls are expected to be frequent and not significantly modify the device's internal state.

2. On device disconnect, nothing happens.

3. On the next attempted Belay call, Belay will begin to attempt to reconnect with the device.
   This inherently resets the device, and consequently resets the device's python interpreter state.

4. Upon reconnection, **Belay will replay the entire call history.**
   For most projects, this should be relatively short and typically includes things like:

   a. File-syncs:  ``device.sync("board/")``

   b. Library imports:  ``device("import mysensor")``

   b. Global object creations:  ``device("sensor = mysensor.Sensor()")``

   c. Task definitions::

          @device.task
          def read_sensor():
              return sensor.read()

   This history replay can result in a longer-than-expected blocking call.


Interface
---------

Belay currently supports two connection interfaces:

1. Serial, typically over a USB cable. Recommended connection method.

2. WebREPL, typically over WiFi. Experimental and relatively slow due to higher command latency.


Serial
^^^^^^
This is the typical connection method over a cable and is fairly self-explanatory.

UDev Rules
**********
To ensure your serial device always connects with the same name, we can create a udev rule.
Invoke ``lsusb`` to figure out some device information; the response should look like:

.. code-block:: bash

   belay:~/belay$ lsusb
   Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
   Bus 001 Device 003: ID 239a:80f4 Adafruit Pico
   Bus 001 Device 002: ID 2109:3431 VIA Labs, Inc. Hub
   Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub

Left of the colon is the 4-character ``idVendor`` value, and right of the colon is the 4-character ``idProduct`` value.
Next, edit a file at ``/etc/udev/rules.d/99-usb-serial.rules`` to contain:

.. code-block:: text

   SUBSYSTEM=="tty", ATTRS{idVendor}=="xxxx", ATTRS{idProduct}=="yyyy", SYMLINK+="target"

For example, the following will map the "Adafruit Pico" to ``/dev/ttyACM10``:

.. code-block:: text

   SUBSYSTEM=="tty", ATTRS{idVendor}=="239a", ATTRS{idProduct}=="80f4", SYMLINK+="ttyACM10"

Finally, the following command will reload the udev rules without having to do a reboot:

.. code-block:: bash

   sudo udevadm control --reload-rules && sudo udevadm trigger

WebREPL
^^^^^^^
WebREPL_ is a protocol for accessing a MicroPython REPL over websockets.

WebREPL requires the MicroPython-bundled ``webrepl`` server running on-device.
To run the WebREPL server on boot, we need two files on device:

1. ``boot.py`` that connects to your WiFi and starts the server.
2. ``webrepl_cfg.py`` that contains the password to access the WebREPL interface.

These files may look like (tested on an ESP32):

.. code-block:: python

   ###########
   # boot.py #
   ###########
   def do_connect(ssid, pwd):
       import network

       sta_if = network.WLAN(network.STA_IF)
       if not sta_if.isconnected():
           print("connecting to network...")
           sta_if.active(True)
           sta_if.connect(ssid, pwd)
           while not sta_if.isconnected():
               pass
       print("network config:", sta_if.ifconfig())


   # Attempt to connect to WiFi network
   do_connect("YOUR WIFI SSID", "YOUR WIFI PASSWORD")

   import webrepl

   webrepl.start()

.. code-block:: python

   ##################
   # webrepl_cfg.py #
   ##################
   PASS = "python"

Once these files are on-device, connect to the device by providing the
correct IP address and password. The ``ws://`` prefix tells Belay to
use WebREPL.

.. code-block:: python

   device = belay.Device("ws://192.168.1.100", password="python")


.. _WebREPL: https://github.com/micropython/webrepl
