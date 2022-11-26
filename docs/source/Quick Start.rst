Quick Start
===========

Belay is a library that makes it quick and easy to interact with hardware via a MicroPython-compatible microcontroller.

Belay has a single imporant class, ``Device``.

.. code-block:: python

   import belay

   device = belay.Device("/dev/ttyUSB0")

Creating a ``Device`` object connects to the board at the provided port.
On connection, the device is reset into REPL mode, and a few common imports are performed on-device, namely:

.. code-block:: python

   import os, time, machine
   from time import sleep
   from micropython import const
   from machine import ADC, I2C, Pin, PWM, SPI, Timer

The ``device`` object has 4 important methods for projects: ``__call__``, ``task``, ``thread``, and ``sync``.
These are described in the subsequent subsections.

Call
^^^^

Directly calling the ``Device`` instance invokes a statement or expression on-device.
For example:

.. code-block:: python

   ret = device("foo = 1 + 2")

would execute the code ``foo = 1 + 2`` on-device.
``ret`` is ``None`` since ``foo = 1 + 2`` is a statement.
Subsequently invoking a pythoon expression like:

.. code-block:: python

   res = device("foo")

results in ``res == 3``.

Direct invocations like this are common to import modules and declare global variables.
Alternative methods are described in the `task`_ section.

task
^^^^

The ``task`` decorator sends the decorated function to the device, and replaces the host function with a remote-executor.

Consider the following:

.. code-block:: python

   @device.task
   def foo(a):
       return a * 2

Invoking ``bar = foo(5)`` on host sends a command to the device to execute the function ``foo`` with argument ``5``.
The result, ``10``, is sent back to the host and results in ``bar == 10``.
This is the preferable way to interact with hardware.

If a task is registered to multiple Belay devices, it will execute sequentially on the devices in the order that they were decorated (bottom upwards).
The return value would be a list of results in order.

To explicitly call a task on just one device, it can be invoked ``device.task.foo()``.

thread
^^^^^^

``thread`` is similar to ``task``, but executes the decorated function in the background on-device.

.. code-block:: python

   @device.thread
   def led_loop(period):
       led = Pin(25, Pin.OUT)
       while True:
           led.toggle()
           sleep(period)


   led_loop(1.0)  # Returns immediately

Not all MicroPython boards support threading, and those that do typically have a maximum of ``1`` thread.
The decorated function has no return value.

If a thread is registered to multiple Belay devices, it will execute sequentially on the devices in the order that they were decorated (bottom upwards).

To explicitly call a thread on just one device, it can be invoked ``device.thread.led_loop()``.

sync
^^^^
For more complicated hardware interactions, additional python modules/files need to be available on the device's filesystem.
``sync`` takes in a path to a local folder.
The contents of the folder will be synced to the device's root directory.

For example, if the local filesystem looks like:

::

    project
    ├── main.py
    └── board
        ├── foo.py
        └── bar
            └── baz.py

Then, after ``device.sync("board")`` is ran from ``main.py``, the remote filesystem will look like

::

    foo.py
    bar
    └── baz.py
