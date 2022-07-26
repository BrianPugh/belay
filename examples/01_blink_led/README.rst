Example 01: Blink LED
=====================

Belay projects are a little bit different from normal python projects.
You are actually writing two different python programs at the same time:

    1. Code that will run in the MicroPython environment on your microcontroller.

    2. Code that will run on your computer and interact with the code in (1).

To run this demo, run:

.. code-block:: bash

   python main.py --port YOUR_DEVICE_PORT_HERE

For example:

.. code-block:: bash

   python main.py --port /dev/ttyUSB0


Code Explanation
^^^^^^^^^^^^^^^^

First import Belay.

.. code-block:: python

   import belay

Next, we will create a ``Device`` object that will connect to the board.

.. code-block:: python

      device = belay.Device("/dev/ttyUSB0")

This also executes some convenience imports on the board, specifically:

.. code-block:: python

   import binascii, errno, hashlib, machine, os, time
   from machine import ADC, I2C, Pin, PWM, SPI, Timer
   from time import sleep
   from micropython import const

We will be only using the ``Pin`` class in this example.
Next, we will decorate a function with the ``task`` decorator.
The function decorated by this decorator will be sent to the board.
The body of this function will never execute on host.

.. code-block:: python

   @device.task
   def set_led(state):
       Pin(25, Pin.OUT).value(state)

The pin number may vary, depending on your hardware setup.
Now that the function ``set_led`` is defined in the board's current environment, we can execute it.
Calling ``set_led(True)`` won't invoke the function on the host, but will send a command to execute it on-device with the argument ``True``.
This results in the LED turning on.
