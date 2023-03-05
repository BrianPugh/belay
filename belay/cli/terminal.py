from typer import Argument, Option

from belay import Device
from belay.cli.common import help_password, help_port


def terminal(
    port: str = Argument(..., help=help_port),
    password: str = Option("", help=help_password),
):
    """Open up an interactive REPL.

    Press ctrl+] to exit.
    """
    with Device(port, password=password) as device:
        device.terminal()
