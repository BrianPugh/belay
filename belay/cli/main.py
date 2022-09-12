from functools import partial
from pathlib import Path
from time import sleep

import typer
from rich.console import Console
from rich.progress import Progress
from typer import Argument, Option

import belay

Arg = partial(Argument, ..., show_default=False)
Opt = partial(Option)

app = typer.Typer()
state = {}
console: Console


@app.callback()
def callback(silent: bool = False):
    """Tool to interact with MicroPython hardware."""
    global console, Progress
    state["silent"] = silent
    console_kwargs = {}
    if state["silent"]:
        console_kwargs["quiet"] = True
    console = Console(**console_kwargs)
    Progress = partial(Progress, console=console)


@app.command()
def sync(
    port: str = Arg(
        help="Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."
    ),
    folder: Path = Arg(help="Path to folder to sync."),
    password: str = Opt(
        "",
        help="Password for communication methods (like WebREPL) that require authentication.",
    ),
):
    """Synchronize a folder to device."""
    with Progress() as progress:
        task_id = progress.add_task("")
        progress_update = partial(progress.update, task_id)
        progress_update(description=f"Connecting to {port}")
        device = belay.Device(port, password=password)
        progress_update(description=f"Connected to {port}.")

        device.sync(folder, progress_update=progress_update)

        progress_update(description="Sync complete.")


@app.command()
def info(
    port: str = Arg(
        help="Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."
    ),
    password: str = Opt(
        "",
        help="Password for communication methods (like WebREPL) that require authentication.",
    ),
):
    """Display device firmware information."""
    device = belay.Device(port, password=password)
    version_str = "v" + ".".join(str(x) for x in device.implementation.version)
    print(
        f"{device.implementation.name} {version_str} - {device.implementation.platform}"
    )
    return device


@app.command()
def identify(
    port: str = Arg(
        help="Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."
    ),
    pin: int = Arg(help="GPIO pin to flash LED on."),
    password: str = Opt(
        "",
        help="Password for communication methods (like WebREPL) that require authentication.",
    ),
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
