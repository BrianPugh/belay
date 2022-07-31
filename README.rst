.. image:: https://media.githubusercontent.com/media/BrianPugh/belay/main/assets/logo_white_400w.png

|Python compat| |PyPi| |GHA tests| |Codecov report| |readthedocs|


Belay
=====

.. inclusion-marker-do-not-remove

Belay is a library that enables the rapid development of projects that interact with hardware via a micropython-compatible board.

`Quick Video of Belay in 22 seconds.`_

Who is Belay For?
=================

Belay is for people creating a software project that needs to interact with hardware.
Examples include:

* Control a motor so a webcam is always pointing at a person.

* Turn on an LED when you receive a notification.

* Read a potentiometer to control system volume.


What Problems Does Belay Solve?
===============================

Typically, having a python script interact with hardware involves 3 major challenges:

1. On-device firmware (usually C or MicroPython) for directly handling hardware interactions. Typically this is developed, compiled, and uploaded as a (nearly) independent project.

2. A program on your computer that performs the tasks specified and interacts with the device.

3. Computer-to-device communication protocol. How are commands and results transferred? How does the device execute those commands?


This is lot of work if you just want your computer to do something simple like turn on an LED.
Belay simplifies all of this by merging steps 1 and 2 into the same codebase, and manages step 3 for you.
Code is automatically synced at the beginning of script execution.

Installation
============

Belay requires Python ``>=3.8`` and can be installed via:

.. code-block:: bash

   pip install belay

The micropython-compatible board only needs micropython installed; no additional preparation is required.

Examples
========

Turning on an LED with Belay takes only 6 lines of code.

.. code-block:: python

   import belay

   device = belay.Device("/dev/ttyUSB0")


   @device.task
   def set_led(state):
       Pin(25, Pin.OUT).value(state)


   set_led(True)


`For more examples, see the examples folder.`_


.. |GHA tests| image:: https://github.com/BrianPugh/belay/workflows/tests/badge.svg
   :target: https://github.com/BrianPugh/belay/actions?query=workflow%3Atests
   :alt: GHA Status
.. |Codecov report| image:: https://codecov.io/github/BrianPugh/belay/coverage.svg?branch=main
   :target: https://codecov.io/github/BrianPugh/belay?branch=main
   :alt: Coverage
.. |readthedocs| image:: https://readthedocs.org/projects/belay/badge/?version=latest
        :target: https://belay.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status
.. |Python compat| image:: https://img.shields.io/badge/>=python-3.8-blue.svg
.. |PyPi| image:: https://img.shields.io/pypi/v/belay.svg
        :target: https://pypi.python.org/pypi/belay
.. _Quick Video of Belay in 22 seconds.: https://www.youtube.com/watch?v=wq3cyjSE8ek
.. _For more examples, see the examples folder.:  https://github.com/BrianPugh/belay/tree/main/examples
