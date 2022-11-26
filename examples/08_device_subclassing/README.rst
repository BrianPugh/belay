Example 08: Device Subclassing
==============================
It may be convenient to organize your Belay tasks into a class
rather than decorated standalone functions.
This also allows for multiple devices to share the same task definitions.
Methods are marked with the ``@Device.task`` decorator; source code
is sent to the device and executers are created when the ``Device`` object
is instantiated.
Methods marked with ``@Device.task`` are similar to ``@staticmethod`` in that
they do **not** contain ``self`` in the method signature.
