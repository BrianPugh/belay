from pathlib import Path

from typer import Argument, Option

from belay import Device
from belay.cli.common import help_password, help_port, remove_stacktrace


def run(
    port: str = Argument(..., help=help_port),
    file: Path = Argument(..., help="File to run on-device."),
    password: str = Option("", help=help_password),
):
    """Run file on-device.

    If the first argument, ``port``, is resolvable to an executable,
    the remainder of the command will be interpreted as a shell command
    that will be executed in a pseudo-micropython-virtual-environment.
    As of right now, this just sets ``MICROPYPATH`` to all of the dependency
    groups' folders. E.g::

            belay run micropython -m unittest

    """
    content = file.read_text()
    with Device(port, password=password) as device, remove_stacktrace():
        device(content)
