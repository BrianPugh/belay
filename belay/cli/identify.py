from pathlib import Path
from time import sleep

from typer import Argument, Option

from belay import Device
from belay.cli.common import help_password, help_port
from belay.cli.info import info


def identify(
    port: str = Argument(..., help=help_port),
    pin: int = Argument(..., help="GPIO pin to flash LED on."),
    password: str = Option("", help=help_password),
    neopixel: bool = Option(False, help="Indicator is a neopixel."),
):
    """Display device firmware information and blink an LED."""
    device = info(port=port, password=password)

    if device.implementation.name == "circuitpython":
        device(f"led = digitalio.DigitalInOut(board.GP{pin})")
        device("led.direction = digitalio.Direction.OUTPUT")

        if neopixel:
            device("from neopixel_write import neopixel_write")

            @device.task
            def set_led(state):
                val = (255, 255, 255) if state else (0, 0, 0)
                val = bytearray(val)
                neopixel_write(led, val)  # noqa: F821

        else:

            @device.task
            def set_led(state):
                led.value = state  # noqa: F821

    else:
        device(f"led = Pin({pin}, Pin.OUT)")

        if neopixel:
            device("import neopixel")
            device("pixel = neopixel.NeoPixel(led, 1)")

            @device.task
            def set_led(state):
                pixel[0] = (255, 255, 255) if state else (0, 0, 0)  # noqa: F821
                pixel.write()  # noqa: F821

        else:

            @device.task
            def set_led(state):
                led.value(state)  # noqa: F821

    while True:
        set_led(True)
        sleep(0.5)
        set_led(False)
        sleep(0.5)
