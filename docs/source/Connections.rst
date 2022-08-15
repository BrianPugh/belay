Connections
===========

Belay currently supports two connection mediums:

1. Serial, typically over a USB cable. Recommended connection method.

2. WebREPL, typically over WiFi. Experimental and relatively slow due to higher command latency.


Serial
^^^^^^
This is the typical connection method over a cable and is fairly self-explanatory.


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
