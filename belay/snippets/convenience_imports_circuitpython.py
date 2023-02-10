import os, time, board, digitalio
from time import sleep
try:
    import analogio
except ImportError:
    pass
try:
    from busio import I2C
except ImportError:
    pass
try:
    from busio import SPI
except ImportError:
    pass
