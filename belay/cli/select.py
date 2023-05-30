import asyncio
import contextlib

import questionary
import typer
from questionary import Choice

from belay import Device, DeviceMeta
from belay.cli.questionary_ext import press_any_key_to_continue, select_table
from belay.usb_specifier import list_devices


async def blink_loop(device):
    while True:
        device.led(True)
        await asyncio.sleep(0.5)
        device.led(False)
        await asyncio.sleep(0.5)


async def blink_until_prompt(device):
    blink_task = asyncio.create_task(blink_loop(device))
    await press_any_key_to_continue().ask_async()
    blink_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await blink_task


class CircuitPythonBlinker(metaclass=DeviceMeta):
    @Device.setup(implementation="circuitpython")
    def setup(pin: str, is_neopixel) -> None:
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
            neopixel_write(led_io, bytearray(val))
        else:
            led_io.value = value

    @Device.teardown(implementation="circuitpython", ignore_errors=True)
    def teardown():
        if is_neopixel:
            neopixel_write(led_io, b"\x00\x00\x00")
        else:
            led_io.value = False


class MicroPythonBlinker(metaclass=DeviceMeta):
    @Device.setup
    def setup(pin, is_neopixel) -> None:
        from machine import Pin

        led_io = Pin(int(pin), Pin.OUT)

        if is_neopixel:
            from neopixel import NeoPixel

            pixel = NeoPixel(led_io, 1)

    @Device.task
    def led(value: bool) -> None:
        if is_neopixel:
            pixel[0] = (255, 255, 255) if value else (0, 0, 0)
            pixel.write()
        else:
            led_io(value)

    @Device.teardown(ignore_errors=True)
    def teardown():
        if is_neopixel:
            pixel[0] = (0, 0, 0)
            pixel.write()
        else:
            led_io(False)


class Blinker(Device, CircuitPythonBlinker, MicroPythonBlinker):
    """MicroPython + CircuitPython led/neopixel interactions."""


def select():
    """Interactive board selector.

    For determining board-specific metadata for repeatable connections.
    """
    style = "bold"
    table_spec = {
        "vid": 6,
        "pid": 6,
        "serial_number": 18,
        "manufacturer": 18,
        "product": 18,
        "location": 18,
    }
    header = " ".join(f"{k:{v}}" for k, v in table_spec.items())
    specs, choices = [], []
    for spec in list_devices():
        specs.append(spec)
        choices.append(
            Choice(
                " ".join(f"{str(getattr(spec, k)):{v}.{v}}" for k, v in table_spec.items()),
                value=len(choices),
            )
        )

    if not choices:
        print("Detected no devices.")
        raise typer.Exit(code=1)

    device_index = select_table(
        "Select USB Device (Use arrow keys):",
        header,
        choices,
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
            is_neopixel = questionary.confirm("Is this a NeoPixel?", default=False).ask()
            device.setup(pin_number, is_neopixel)

            asyncio.run(blink_until_prompt(device))

    spec_json = spec.json(exclude_none=True)
    questionary.print("\n")
    questionary.print("Either set the BELAY_DEVICE environment variable:", style=style)
    questionary.print(f"    export BELAY_DEVICE='{spec_json}'")
    questionary.print("And in python code, instantiate Device without arguments:", style=style)
    questionary.print("    device = belay.Device()")
    questionary.print("")
    questionary.print("Or, add the following (or a subset) to your python code:", style=style)
    questionary.print(f"    spec = belay.{spec!r}\n    device = belay.Device(spec)\n")
