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

Belay contains a small collections of decorators that shuttle code and commands to a micropython board.
The body of decorated functions *always* execute on-device; never on host.

Using the ``setup`` decorator, define a function to import the ``Pin`` class and create an object representing an LED.
We don't strictly need to import ``Pin`` since its included in Belay's `convenience imports`_, but do so here for clarity.
The pin number may vary, depending on your hardware setup.
``setup`` decorated functions do not do anything until invoked.

.. code-block:: python

   @device.setup
   def setup():  # The function name doesn't matter, but is "setup" by convention.
       from machine import Pin

       led = Pin(25, Pin.OUT)


Next, we will decorate a function with the ``task`` decorator.
The source code of the function decorated by ``task`` will be *immediately* sent to the board.

.. code-block:: python

   @device.task
   def set_led(state):
       print(f"Printing from device; turning LED to {state}.")
       led.value(state)

Now that the function ``set_led`` is defined in the board's current environment, we can execute it.
Calling ``set_led(True)`` won't invoke the function on the host, but will send a command to execute it on-device with the argument ``True``.
On-device ``print`` calls have their results forwarded to the host's ``stdout``.
This results in the LED turning on.

.. _convenience imports: https://github.com/BrianPugh/belay/blob/main/belay/snippets/convenience_imports_micropython.py
