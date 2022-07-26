Example 05: Exceptions
======================

This example shows what happens when an uncaught exception occurs on-device.

When an uncaught exception occurs on-device, a ``PyboardException`` is raised on the host.
The message of the ``PyboardException`` contains the on-device stack trace.
The stack trace is modified by Belay to reinterpret file and line numbers to their original sources defined in the program on-host.

The on-host traceback should look like:

.. code-block:: bash

      File "/home/user/.local/lib/python3.8/site-packages/belay/pyboard.py", line 475, in exec_
        raise PyboardException(ret_err.decode())
    belay.pyboard.PyboardException:

    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "<stdin>", line 4, in belay_interface
      File "/projects/belay/examples/05_exception/main.py", line 15, in f
        raise Exception("This is raised on-device.")
    Exception: This is raised on-device.
