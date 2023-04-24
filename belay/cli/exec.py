from pathlib import Path

from typer import Argument, Option

from belay import Device
from belay.cli.common import help_password, help_port, remove_stacktrace


def exec(
    port: str = Argument(..., help=help_port),
    statement: str = Argument(..., help="Statement to execute on-device."),
    password: str = Option("", help=help_password),
):
    """Execute python statement on-device."""
    device = Device(port, password=password)
    with remove_stacktrace():
        device(statement)
    device.close()
