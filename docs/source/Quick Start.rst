Quick Start
===========

Belay is a library that makes it quick and easy to interact with hardware via a MicroPython-compatible microcontroller.
Belay has a single important class, ``Device``:

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

The ``Device`` class has several useful methods:

1. ``__call__`` - Generic statement/expression string evaluation.

2. ``setup`` - Executes body on-device in a global context.

3. ``task`` - Executes function on-device.

4. ``teardown`` - Executes body on-device in a global context when connection is closed.

5. ``thread`` - Executes function on-device in a background thread.

6. ``sync`` - Generic file synchronization from host to device.

7. ``sync_dependencies`` - For python packages to sync bundled micropython dependencies to board.

These are described in more detail in the subsequent subsections.

call
^^^^

Directly calling the ``device`` instance, like a function, invokes a python statement or expression on-device.

Invoking a python statement like:

.. code-block:: python

   ret = device("foo = 1 + 2")

would execute the code ``foo = 1 + 2`` on-device in the global context.
Because this is a statement, the return value, ``ret`` is ``None``.

Invoking a python expression like:

.. code-block:: python

   res = device("foo")

results in the return value ``res == 3`` on host.

setup
^^^^^
The ``setup`` decorator is a way of invoking code on-device in a global context,
and is commonly used for imports and instantiating objects and hardware.
For example:

.. code-block:: python

   @device.setup
   def setup(pin_number):
       from machine import Pin

       led = Pin(pin_number)


   setup(25)

is equivalent to:

.. code-block:: python

   device("pin_number = 25")
   device("from machine import Pin")
   device("led = Pin(pin_number)")

Functions decorated with ``setup`` should be called only a few times at most.
For repeated functions calls, use the `task`_ decorator.

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

Alternatively, the ``foo`` function will also be available at ``device.task.foo``.

teardown
^^^^^^^^
Same as ``setup``, but automatically executes whenever ``device.close()`` is called.
If ``Device`` is used as a context manager, ``device.close()`` is automatically called at context manager exit.
Typically used for cleanup, like turning off LEDs or motors.

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

sync_dependencies
^^^^^^^^^^^^^^^^^
Syncs data that has been bundled with a python package.
``sync_dependencies`` is intended to make including micropython dependencies easier for pip-installable host-program.

.. code-block:: python

   from belay import Device

   device = Device("/dev/ttyUSB0")

   device.sync_dependencies("mypackage", "board")
   # Alternative usage
   import mypackage

   device.sync_dependencies(mypackage, "board")

An intended use-case is to this method inconjunction with Belay's builtin package manager.
Configure ``dependencies_path`` in ``pyproject.toml`` to point inside your python package, i.e. ``dependencies_path="mypackage/dependencies"``.
In doing so, micropython dependencies will be stored inside your package.
For this example, lets assume that ``pyproject.toml`` defines ``main`` and ``dev`` dependencies.
The data can then be synced:

.. code-block:: python

   device.sync_dependencies(mypackage, "dependencies/main", "dependencies/dev")

Depending on your build system, other non-belay configurations *may* need to be performed to ensure other data is included in your python package.

Subclassing Device
^^^^^^^^^^^^^^^^^^
``Device`` can be subclassed and have task/thread methods. Benefits of this approach is better organization, and being able to define tasks/threads before the actual object is instantiated.

Consider the following:

.. code-block:: python

   from belay import Device

   device = Device("/dev/ttyUSB0")


   @device.task
   def foo(a):
       return a * 2

is roughly equivalent to:

.. code-block:: python

   from belay import Device


   class MyDevice(Device):
       @Device.task
       def foo(a):
           return a * 2


   device = MyDevice("/dev/ttyUSB0")

Marking methods as tasks/threads in a class requires using the capital ``@Device.task`` decorator.
Methods marked with ``@Device.task`` are similar to ``@staticmethod`` in that
they do **not** contain ``self`` in the method signature.
To the device, each marked method is equivalent to an independent function.
Methods can be marked with ``@Device.setup`` or ``@Device.thread`` for their respective functionality.
Methods not marked with these decorators are just normal, boring python methods.

For methods decorated with ``@Device.setup``, the flag ``autoinit=True`` can be set to automatically
call the method at the end of object creation.
The decorated method must have no parameters, otherwise a ``ValueError`` will be raised.

.. code-block:: python

   from belay import Device


   class MyDevice(Device):
       @Device.setup(autoinit=True)
       def setup():
           foo = 42


   device = MyDevice("/dev/ttyUSB0")
   # Do NOT explicitly call ``device.setup()``, it has already been invoked.

The ``Device`` class also has some hook methods that can be implemented to give customization to the object initialization process:

1. ``__pre_autoinit__`` - Called near the end of ``__init__``, after convenience imports have been imported, but before methods marked with ``@Device.setup(autoinit=True)`` are invoked. This is a good location to sync additional micropython dependencies to device.

2. ``__post_init__`` -  Called at the very end of ``__init__``. This is a good location to set custom object attributes.

The following example will (in order):

1. Synchronize code located at ``dependencies/main`` within ``my_package`` to on-device ``/lib``.

2. On-device, declare the global variable ``operation_mode_pin`` representing an input on pin 10.

3. On-host, query ``operation_mode_pin`` and set the attribute ``operation_mode``, which could be used in other host methods.


.. code-block:: python

   from belay import Device


   class MyDevice(Device):
       def __pre_autoinit__(self):
           # runs before ``setup(autoinit=True)`` decorated methods
           self.sync_dependencies("my_package", "dependencies/main")

       @Device.setup(autoinit=True)
       def setup():
           # A hypothetical jumper that controls how the device should function.
           operation_mode_pin = Pin(10, Pin.IN, Pin.PULL_UP)

       def __post_init__(self):
           # runs after ``setup(autoinit=True)`` decorated methods
           if self("operation_mode_pin.value"):
               self.operation_mode = "dev"
           else:
               self.operation_mode = "prod"
