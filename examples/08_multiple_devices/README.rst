Example 08: Multiple Devices
============================

Belay can interact with multiple micropython boards on different ports.
Tasks and Threads can be decorated multiple times from different devices.
When executed, devices are executed in the order that they were decorated (bottom upwards).
