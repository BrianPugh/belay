from machine import Pin


def set(pin, value):
    Pin(pin, Pin.OUT).value(value)
