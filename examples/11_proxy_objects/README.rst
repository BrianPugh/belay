=========================
Example 11: Proxy Objects
=========================

This example shows how to use ``belay.ProxyObject``. A proxy object forwards all attribute read/writes, as well as all method calls, to the remote micropython object.

.. code-block:: bash

   $ python main.py --port /dev/ttyUSB0
   We got the attribute "Bob Smith".
   We executed the method "greetings" and got the result: "Hello Bob Smith!"
