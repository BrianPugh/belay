How Belay Works
===============

In a nutshell, Belay sends python code (plain text) over the serial connection to the
device's MicroPython Interactive Interpreter Mode (REPL) and parses back the response.

The easiest way to explain it is to walk through what's going under the hood with an example.

Device Creation
^^^^^^^^^^^^^^^

.. code-block:: python

   device = belay.Device("/dev/ttyUSB0")

This creates a :class:`~belay.Device` object that connects to the microcontroller.
Belay resets it, enters REPL mode, and then runs `some convenience imports on the board`_.


Task - Sending Code Over
^^^^^^^^^^^^^^^^^^^^^^^^

Consider the following decorated function:

.. code-block:: python

   @device.task
   def set_led(state):
       """This function sets a pin to the specified state."""
       Pin(25, Pin.OUT).value(state)  # Set a pin as an output, and set its value

The :meth:`~belay.Device.task` decorator inspects the actual code of the function its decorating and sends it over to the microcontroller.
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

After minification, the function code is sent directly to the device and executed. The minified function
is stored on the device exactly as written:

.. code-block:: python

   def set_led(state):
    0
    Pin(25,Pin.OUT).value(state)

This function can now be called from other on-device code, or invoked from the host computer.
When invoked from the host, Belay handles the serialization and deserialization of arguments and return values.


Task - Executing Function
^^^^^^^^^^^^^^^^^^^^^^^^^

Now that the function has been sent over and parsed by the microcontroller, we would like to execute it.
The :meth:`~belay.Device.task` decorator returns a function that when invoked, creates and sends a command to the device,
and then parses back the response. The complete lifecycle looks like this:

1. ``set_led(True)`` is called on the host. This doesn't execute the function we defined on host. Instead it triggers the following actions.

2. Belay creates the function call expression ``"set_led(True)"``.

3. Since this is an expression, Belay wraps it with serialization code on the host side: ``'print("_BELAYR|"+repr(set_led(True)))'``.

4. Belay sends this wrapped command over serial to the REPL, causing it to execute on-device.

5. On-device, ``set_led(True)`` executes and returns :py:obj:`None`. This gets serialized via :py:func:`repr` and printed with the ``_BELAYR|`` prefix.

6. Belay reads the response ``_BELAYR|None`` from stdout, strips the prefix, and deserializes it back to the :py:obj:`None` object using :py:func:`ast.literal_eval`.

7. :py:obj:`None` is returned on host from the ``set_led(True)`` call.

This has a few limitations, namely:

1. Each passed in argument must be a python literal (:py:obj:`None`, booleans, bytes, numbers, strings, sets, lists, and dicts).

2. User code cannot print a message that begins with ``_BELAY``, otherwise the remainder of the message will attempt to be parsed.

3. By default, returned data must be a python literal that can be safely parsed by :py:func:`ast.literal_eval`. For more complex objects, you can either:

   a. Use :meth:`@device.task(trusted=True) <belay.Device.task>` to allow :py:func:`eval` instead (security risk - only use with trusted code)

   b. Use :meth:`device.proxy("obj_name") <belay.Device.proxy>` to create a :class:`~belay.ProxyObject` that allows you to interact with remote objects that cannot be serialized


Response Format
^^^^^^^^^^^^^^^

Belay uses special markers in the device output to identify responses:

- ``_BELAYR|<timestamp>|<value>`` - Normal return value with optional timestamp. When time synchronization is enabled, the timestamp (in milliseconds) is included to track when the result was generated on the device. The value is deserialized and returned to the host.

- ``_BELAYR<id>|<timestamp>|`` - :class:`~belay.ProxyObject` reference with optional timestamp. The object is stored on-device as ``__belay_obj_<id>`` and a :class:`~belay.ProxyObject` is returned on the host that can interact with it remotely.

- ``_BELAYS`` - StopIteration marker used for generator functions.

This protocol allows Belay to distinguish between user output and command results.


.. _some convenience imports on the board: https://github.com/BrianPugh/belay/blob/main/belay/snippets/convenience_imports_micropython.py
