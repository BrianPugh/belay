How Belay Works
===============

In a nutshell, Belay sends python code (plain text) over the serial connection to the
device's MicroPython Interactive Interpreter Mode (REPL) and parses back the response.

The easiest way to explain it is to walk through what's going under the hood with an example.

Device Creation
^^^^^^^^^^^^^^^

.. code-block:: python

   device = belay.Device("/dev/ttyUSB0")

This creates a ``Device`` object that connects to the microcontroller.
Belay resets it, enters REPL mode, and then runs `some convenience imports on the board`_.


Task - Sending Code Over
^^^^^^^^^^^^^^^^^^^^^^^^

Consider the following decorated function:

.. code-block:: python

   @device.task
   def set_led(state):
       """This function sets a pin to the specified state."""
       Pin(25, Pin.OUT).value(state)  # Set a pin as an output, and set its value

The ``task`` decorator inspects the actual code of the function its decorating and sends it over to the microcontroller.
Prior to sending the code over, a few preprocessing steps are required.
At first, the code looks like:

.. code-block:: python

   def set_led(state):
       """This function sets a pin to the specified state."""
       Pin(25, Pin.OUT).value(state)  # Set a pin as an output, and set its value

Belay can only send around 25,600 characters a second, so we want to reduce the amount of unnecessary characters.
Some minification is performed to reduce the number of characters we have to send over to the device.
The minification removes docstrings, comments, and unnecessary whitespace.
Dont hesitate to add docstrings and comments to your code, they'll be stripped away before they reach your microcontroller.
The minification maintains all variable names and line numbers, which can be important for debugging.
After minification, the code looks like:

.. code-block:: python

   def set_led(state):
    0
    Pin(25,Pin.OUT).value(state)

The ``0`` is just a one character way of saying ``pass``, in case the removed docstring was the entire body.
This reduces the number of transmitted characters from 158 to just 53, offering a 3x speed boost.

After minification, the ``@__belay`` decorator is added. On-device, this defines a variant of the function, ``_belay_FUNCTION_NAME``
that performs the following actions:

 1. Takes the returned value of the function, and serializes it to a string using ``repr``.

 2. Prints the resulting string to stdout, so it can be read by the host computer and deserialized via ``ast.literal_eval``.


Conceptually, its as if the following code ran on-device (minification removed for clarity):

.. code-block:: python

   def set_led(state):
       Pin(25, Pin.OUT).value(state)


   def _belay_set_led(*args, **kwargs):
       res = set_led(*args, **kwargs)
       print("_BELAYR" + repr(res))

A separate private function is defined with this serialization in case another on-device function calls ``set_led``.


Task - Executing Function
^^^^^^^^^^^^^^^^^^^^^^^^^

Now that the function has been sent over and parsed by the microcontroller, we would like to execute it.
The ``@task`` decorator returns a function that when invoked, creates and sends a command to the device,
and then parses back the response. The complete lifecycle looks like this:

1. ``set_led(True)`` is called on the host. This doesn't execute the function we defined on host. Instead it triggers the following actions.

2. Belay creates the string ``"_belay_set_led(True)"``.

3. Belay sends this command over serial to the REPL, causing it to execute on-device.

4. On-device, the result of ``set_led(True)`` is ``None``. This gets serialized to the string ``None``, which gets printed to stdout.

5. Belay reads this response form stdout, and deserializes it back to the ``None`` object.

6. ``None`` is returned on host from the ``set_led(True)`` call.

This has a few limitations, namely:

1. Each passed in argument must be a python literals (``None``, booleans, bytes, numbers, strings, sets, lists, and dicts).

2. User code cannot print a message that begins with ``_BELAY``, otherwise the remainder of the message will attempt to be parsed.

3. The returned data of the function must also be a python literal(s).



.. _some convenience imports on the board: https://github.com/BrianPugh/belay/blob/main/belay/snippets/convenience_imports_micropython.py
