Example 08: Multiple Devices
============================

Belay can interact with multiple micropython boards on different ports.
Tasks and Threads can be decorated multiple times from different devices.
When invoked, the resulting decorated function will execute on the devices in the order that they were decorated (bottom upwards).

To execute a task on just one specific device, it can be accessed like ``device1.task.set_led``.
Similarly, to execute a thread on just one specific device, call ``device1.thread.blink_loop``.
