import os, time, machine
from time import sleep
from micropython import const
from machine import Pin, PWM, Timer
try:
    from machine import I2C
except ImportError:
    pass
try:
    from machine import SPI
except ImportError:
    pass
try:
    from machine import ADC
except ImportError:
    pass
