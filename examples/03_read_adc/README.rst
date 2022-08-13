Example 03: Read ADC
====================

This example reads the temperature in celsius from the RP2040's internal temperature sensor.
To do this, we explore a new concept: functions can return a value.

Return values are serialized on-device and deserialized on-host by Belay.
This is seamless to the user; the function ``read_temperature`` returns a float on-device, and that same float is returned on the host.

Due to how Belay serializes and deserializes data, only python literals (`None`, booleans, bytes, numbers, strings, sets, lists, and dicts) can be returned.
