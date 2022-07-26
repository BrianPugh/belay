Example 03: Read ADC
====================

This example reads the temperature in celsius from the RP2040's internal temperature sensor.
To do this, we explore a new concept: functions can return a value.

Internally, the values returned by a function executed on-device are serialized to json and sent to the computer.
The computer then deserializes the data and returned the value.
This is seamless to the user; the function ``read_temperature`` returns a float on-device, and that same float is returned on the host.

An implication of this is that only json-compatible datatypes (booleans, numbers, strings, lists, and dicts) can be returned.
