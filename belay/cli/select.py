import questionary
from questionary import Choice

from belay import Device, DeviceMeta
from belay.helpers import list_devices


class CircuitPythonLed(metaclass=DeviceMeta):
    @Device.setup
    def setup_led(self, pin) -> None:
        import board
        import digitalio

        pin_name = "LED" if pin.lower() == "led" else f"GP{pin}"

        led = digitalio.DigitalInOut(getattr(board, pin_name, None))
        led.direction = digitalio.Direction.OUTPUT

    @Device.task(implementation="circuitpython")
    def led(self, value: bool) -> None:
        raise NotImplementedError


class CircuitPythonNeoPixel(metaclass=DeviceMeta):
    @Device.setup
    def setup_neopixel(self, pin) -> None:
        import board
        import digitalio
        from neopixel import neopixel

        pin_name = "LED" if pin.lower() == "led" else f"GP{pin}"

        led = digitalio.DigitalInOut(getattr(board, pin_name, None))
        led.direction = digitalio.Direction.OUTPUT

    @Device.task(implementation="circuitpython")
    def led(self, value: bool) -> None:
        raise NotImplementedError


class MicroPythonLed(metaclass=DeviceMeta):
    @Device.setup
    def setup_led(self, pin) -> None:
        raise NotImplementedError

    @Device.task
    def led(self, value: bool) -> None:
        raise NotImplementedError


class MicroPythonNeoPixel(metaclass=DeviceMeta):
    @Device.setup
    def setup_neopixel(self, pin) -> None:
        raise NotImplementedError

    @Device.task
    def led(self, value: bool) -> None:
        raise NotImplementedError


class Blinker(
    Device, CircuitPythonLed, CircuitPythonNeoPixel, MicroPythonLed, MicroPythonNeoPixel
):
    pass


def select():
    """Interactive board selector.

    For determining board-specific metadata for repeatable connections.
    """
    header = (
        "   "
        f"{'vid':6} "
        f"{'pid':6} "
        f"{'serial_number':18} "
        f"{'manufacturer':18} "
        f"{'product':18} "
        f"{'location':18}"
    )
    devices, choices = [], []
    for device in list_devices():
        devices.append(device)
        choices.append(
            Choice(
                f"{str(device.vid) or '':6.6} "
                f"{str(device.pid) or '':6.6} "
                f"{str(device.serial_number) or '':18.18} "
                f"{str(device.manufacturer) or '':18.18} "
                f"{str(device.product) or '':18.18} "
                f"{str(device.location) or '':18.18}",
                value=len(choices),
            )
        )

    while True:
        device_index = questionary.select(
            f"What do you want to do? (Use arrow keys)\n{header}",
            choices=choices,
            instruction=" ",
        ).ask()

        device = devices[device_index]

        def validate_led_pin_number(response):
            if not response:
                return True

            try:
                int(response)
            except ValueError:
                return False
            return True

        pin_number = questionary.text(
            "Blink LED Pin number [skip]?",
            validate=validate_led_pin_number,
        ).ask()
        if pin_number:
            is_neopixel = questionary.confirm("Is this a NeoPixel?").ask()
            if is_neopixel:
                pass
            else:
                pass
            raise NotImplementedError

        break

    device_json = device.json(exclude_none=True)
    style = "bold"
    questionary.print("Either set the BELAY_DEVICE environment variable:", style=style)
    questionary.print(f"    export BELAY_DEVICE='{device_json}'")
    questionary.print(
        "And in python code, instantiate Device without arguments:", style=style
    )
    questionary.print("    device = belay.Device()")
    questionary.print("")
    questionary.print(
        "Or, add the following (or a subset) to your python code:", style=style
    )
    questionary.print(f"    spec = belay.{device!r}\n    device = belay.Device(spec)\n")
