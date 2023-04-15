from threading import Thread
from time import sleep

import questionary
from questionary import Choice

from belay import Device, DeviceMeta
from belay.helpers import list_devices


def blink_loop(device):
    while True:
        device.led(True)
        sleep(0.5)
        device.led(False)
        sleep(0.5)


class CircuitPythonBlinker(metaclass=DeviceMeta):
    @Device.setup(implementation="circuitpython")
    def setup_meow(pin: str, is_neopixel) -> None:
        import board
        import digitalio

        if is_neopixel:
            from neopixel_write import neopixel_write

        pin_name = "GP"
        pin_name = "LED" if pin.upper() == "LED" else f"GP{pin}"

        led_io = digitalio.DigitalInOut(getattr(board, pin_name))
        led_io.direction = digitalio.Direction.OUTPUT

    @Device.task(implementation="circuitpython")
    def led(value: bool) -> None:
        if is_neopixel:
            val = (255, 255, 255) if value else (0, 0, 0)
            neopixel_write(led_io, bytearray(val))  # noqa: F821
        else:
            led_io.value = value

    @Device.teardown(implementation="circuitpython")
    def teardown():
        if is_neopixel:
            neopixel_write(led_io, b"\x00\x00\x00")  # noqa: F821
        else:
            led_io.value = False


class MicroPythonBlinker(metaclass=DeviceMeta):
    @Device.setup
    def setup_meow(pin, is_neopixel) -> None:
        from machine import Pin

        led_io = Pin(pin, Pin.OUT)

        if is_neopixel:
            from neopixel import NeoPixel

            NeoPixel(led_io, 1)

    @Device.task
    def led(value: bool) -> None:
        if is_neopixel:
            pixel[0] = (255, 255, 255) if value else (0, 0, 0)  # noqa: F821
            pixel.write()  # noqa: F821
        else:
            led_io(value)

    @Device.teardown
    def teardown_neopixel():
        if is_neopixel:
            pixel[0] = (0, 0, 0)  # noqa: F821
            pixel.write()  # noqa: F821
        else:
            led_io(False)


class Blinker(Device, CircuitPythonBlinker, MicroPythonBlinker):
    """MicroPython + CircuitPython led/neopixel interactions."""


def select():
    """Interactive board selector.

    For determining board-specific metadata for repeatable connections.
    """
    style = "bold"
    header = (
        "   "
        f"{'vid':6} "
        f"{'pid':6} "
        f"{'serial_number':18} "
        f"{'manufacturer':18} "
        f"{'product':18} "
        f"{'location':18}"
    )
    specs, choices = [], []
    for spec in list_devices():
        specs.append(spec)
        choices.append(
            Choice(
                f"{str(spec.vid) or '':6.6} "
                f"{str(spec.pid) or '':6.6} "
                f"{str(spec.serial_number) or '':18.18} "
                f"{str(spec.manufacturer) or '':18.18} "
                f"{str(spec.product) or '':18.18} "
                f"{str(spec.location) or '':18.18}",
                value=len(choices),
            )
        )

    while True:
        device_index = questionary.select(
            f"Select USB Device (Use arrow keys):\n{header}",
            choices=choices,
            instruction=" ",
        ).ask()

        spec = specs[device_index]

        with Blinker(spec) as device:
            questionary.print(str(device.implementation), style=style)

            def validate_led_pin_number(response):
                if not response:
                    return True

                try:
                    int(response)
                except ValueError:
                    return False
                return True

            pin_number = questionary.text(
                "Blink LED Pin Number [skip]?",
                validate=validate_led_pin_number,
            ).ask()

            if pin_number:
                is_neopixel = questionary.confirm(
                    "Is this a NeoPixel?", default=False
                ).ask()
                device.setup_meow(pin_number, is_neopixel)

                # thread = Thread(target=blink_loop, args=(device,))
                # thread.daemon = True
                # thread.start()
                while True:
                    device.led(True)
                    sleep(0.5)
                    device.led(False)
                    sleep(0.5)

                questionary.text("Press enter to continue")

            break

    spec_json = spec.json(exclude_none=True)
    questionary.print("Either set the BELAY_DEVICE environment variable:", style=style)
    questionary.print(f"    export BELAY_DEVICE='{spec_json}'")
    questionary.print(
        "And in python code, instantiate Device without arguments:", style=style
    )
    questionary.print("    device = belay.Device()")
    questionary.print("")
    questionary.print(
        "Or, add the following (or a subset) to your python code:", style=style
    )
    questionary.print(f"    spec = belay.{device!r}\n    device = belay.Device(spec)\n")
