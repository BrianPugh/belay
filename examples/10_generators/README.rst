Example 10: Generators
======================

In Python, a Generator is a function that behaves like an iterator via the ``yield`` keyword.

The following sends the function ``count`` to device.
``count`` counts from 0 to 10 (inclusive), on even numbers turns the LED off, and on odd numbers turns the LED on.

.. code-block:: python

    @device.task
    def count():
        i = 0
        while True:
            Pin(25, Pin.OUT).value(i % 2)
            yield i
            if i >= 10:
                break
            i += 1

On-host, invoking this iterator outputs the yielded value:

.. code-block:: python

    for index in count():
        time.sleep(0.5)
        print(index)

results in:

.. code-block:: text

   0
   1
   2
   3
   4
   5
   6
   7
   8
   9
   10
