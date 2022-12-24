from pathlib import Path

from typer import Argument, Option

from belay import Device
from belay.cli.common import help_password, help_port


def run(
    port: str = Argument(..., help=help_port),
    file: Path = Argument(..., help="File to run on-device."),
    password: str = Option("", help=help_password),
):
    """Run file on-device.

    If the first argument, ``port``, begins with "exec:", the remainder
    of the command will be interpreted as a shell command that will
    be executed in a pseudo-micropython-virtual-environment. As of
    right now, this just sets ``MICROPYPATH`` to all of the dependency
    groups' folders.
    """
    device = Device(port, password=password)
    content = file.read_text()
    device(content)
    device.close()
