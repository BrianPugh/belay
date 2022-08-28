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


.. _CircuitPython: https://circuitpython.org
