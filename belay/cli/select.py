import questionary

from belay import Device


class Blinker(Device):
    def setup_neopixel(self):
        if self.implementation.name == "circuitpython":
            raise NotImplementedError
        else:
            raise NotImplementedError

    def setup_led(self):
        if self.implementation.name == "circuitpython":
            raise NotImplementedError
        else:
            raise NotImplementedError


def select():
    """Interactive board selector.

    For determining board-specific metadata for repeatable connections.
    """
    pass
