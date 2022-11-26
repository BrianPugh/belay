Example 08: Device Subclassing
==============================
It may be convenient to organize your Belay tasks into a class
rather than decorated standalone functions.
To accomplish this, have your class inherit from ``Device``,
and mark methods with the ``@Device.task`` decorator.
Source code of marked methods are sent to the device and executers
are created when the ``Device`` object is instantiated.
This also allows for multiple devices to share the same task definitions
by instantiating multiple objeccts.

Methods marked with ``@Device.task`` are similar to ``@staticmethod`` in that
they do **not** contain ``self`` in the method signature. To the device, each
marked method is equivalent to an independent function.
