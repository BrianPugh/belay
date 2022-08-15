Example 09: WebREPL
===================

First, run the code using the serial port so that the configurations in the ``board/`` folder are synced to device.

.. code-block: bash

   python main.py --port /dev/ttyUSB0

You can then get the IP address by examining the terminal output on boot, or looking at your router configuration.

.. code-block: bash

   mpremote connect /dev/ttyUSB0

This should return something like:

.. code-block: text

   Connected to MicroPython at /dev/tty.usbserial-0001
   Use Ctrl-] to exit this shell
   OK
   MPY: soft reboot
   connecting to network...
   network config: ('192.168.1.110', '255.255.255.0', '192.168.1.1', '192.168.1.1')
   WebREPL daemon started on ws://192.168.1.110:8266
   Started webrepl in normal mode
   raw REPL; CTRL-B to exit
   >

.. code-block: bash

   python main.py --port ws://192.168.1.110


https://micropython.org/webrepl/
