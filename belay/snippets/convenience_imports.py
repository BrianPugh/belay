import binascii, errno, os, time
from time import sleep
if sys.implementation.name == "circuitpython":
    import analogio, board, digitalio
    from busio import I2C, SPI
else:
    import hashlib, machine
    from micropython import const
    from machine import ADC, I2C, Pin, PWM, SPI, Timer
