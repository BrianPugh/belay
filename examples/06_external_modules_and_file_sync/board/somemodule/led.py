from machine import Pin


def set(pin, value):
    # Configuration for a RP2040-ZERO board.
    Pin(pin, Pin.OUT).value(value)
