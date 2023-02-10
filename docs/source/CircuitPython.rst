CircuitPython
=============

Belay also supports CircuitPython_.
Unlike MicroPython, CircuitPython automatically mounts the device's filesystem as a USB drive.
This is usually convenient, but it makes the filesystem read-only to the python interpreter.
To get around this, we need to manually add the following lines to ``boot.py`` on-device.

.. code-block:: python

   import storage

   storage.remount("/")

Afterwards, reset the device and it's prepared for Belay.


Reverting
^^^^^^^^^

To revert this configuration, there are multiple options:

1. Edit ``boot.py`` using Thonny_, then reboot. Thonny (like Belay), operates via the REPL,
   so it has write-access since it's operating through circuitpython.

2. Using Belay in an interactive python prompt:

.. code-block:: python

   from belay import Device

   device = Device("/dev/ttyUSB0")  # replace with appropriate port
   device("os.remove('boot.py')")
   # Then reboot.

Physical Configuration
^^^^^^^^^^^^^^^^^^^^^^
If desired, storage mounting can be configured based on a physical pin state.
Adding the following contents to ``/boot.py`` will configure the system to:

* Be in "normal" circuitpython mode if pin 14 is floating/high (due to
  configured pullup) on boot.

* Be in Belay-compatible mode if pin 14 is connected to ground on boot.
  This could be done, for example, by a push-button or a toggle switch.

.. code-block:: python

   import board
   import storage
   from digitalio import DigitalInOut, Pull

   op_mode = DigitalInOut(board.GP14)  # Choose whichever pin you would like
   op_mode.switch_to_input(Pull.UP)

   if not op_mode.value:
       # Mount system in host-readonly, circuitpython-writeable mode (Belay compatible).
       storage.remount("/")



.. _CircuitPython: https://circuitpython.org
.. _Thonny: https://thonny.org
