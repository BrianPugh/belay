Example 08B: Device Subclassing
==============================
This is an alternative version of Example 08 that explicitly separates
code that runs on the host (``main.py``, ``main_multiple_devices``)
from the class that contains the code (``MyDevice`` in ``mydevice.py``)
that will be pushed to the microcontroller.

It may be convenient to organize your Belay tasks into a class
rather than decorated standalone functions.
To accomplish this, have your class inherit from ``Device``,
and mark methods with the ``@Device.task`` decorator.
Source code of marked methods are sent to the device and executers
are created when the ``Device`` object is instantiated.
This also allows for multiple devices to share the same task definitions
by instantiating multiple objeccts.

Methods marked with ``@Device.setup`` are executed in a global scope. Essentially
the contents of the method are extracted and then executed on the device.
This means any variables created in ``@Device.setup`` are available to any of the
other functions run on the device.

Methods marked with ``@Device.task`` are similar to ``@staticmethod`` in that
they do **not** contain ``self`` in the method signature.
To the device, each marked method is equivalent to an independent function.
