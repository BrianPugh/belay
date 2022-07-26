Example 02: Blink NeoPixel
==========================

This example is similar to example 1, but with a neopixel (intended for the RP2040-Zero board).

However, this example does introduce one new concept.
You can execute an arbitrary string python command on the board by calling your device object:

.. code-block:: python

   device("import neopixel")

This will execute ``import neopixel`` on-device, so the ``neopixel`` module will be available inside of the ``set_neopixel`` function.
Typically, this technique is used for importing modules and defining global variables.
