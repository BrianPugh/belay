from typer import Argument, Option

from belay import Device
from belay.cli.common import help_password, help_port


def info(
    port: str = Argument(..., help=help_port),
    password: str = Option("", help=help_password),
):
    """Display device firmware information."""
    device = Device(port, password=password)
    version_str = "v" + ".".join(str(x) for x in device.implementation.version)
    print(
        f"{device.implementation.name} {version_str} - {device.implementation.platform}"
    )
    device.close()
