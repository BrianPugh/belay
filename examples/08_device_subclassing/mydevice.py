from belay import Device


class MyDevice(Device):
    # NOTE: ``Device`` is capatalized here!
    @Device.setup(
        autoinit=True
    )  # ``autoinit=True`` means this method will automatically be called during object creation.
    def setup():
        # Code here is executed on-device in a global context.
        try:
            # RP2040 wifi plus others
            led_pin = Pin.board.LED
        except (TypeError, AttributeError):
            led_pin = Pin(25, Pin.OUT)  # Example RP2040 w/o wifi
        # ADC4 is attached to an internal temperature sensor on the Pi Pico
        sensor_temp = ADC(4)

    @Device.task
    def set_led(state):
        led_pin.value(state)

    @Device.task
    def read_temperature():
        reading = sensor_temp.read_u16()
        reading *= 3.3 / 65535  # Convert reading to a voltage.
        temperature = 27 - (reading - 0.706) / 0.001721  # Convert voltage to Celsius
        return temperature
