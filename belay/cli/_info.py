from typing import Optional

from belay import Device
from belay.cli.main import app


@app.command
def info(
    port: str,
    *,
    password: Optional[str] = None,
):
    """Display device firmware information.

    Parameters
    ----------
    port: str
        Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device.
    password: Optional[str]
        Password for communication methods (like WebREPL) that require authentication.
    """
    kwargs = {}
    if password is not None:
        kwargs["password"] = password
    with Device(port, **kwargs) as device:
        version_str = "v" + ".".join(str(x) for x in device.implementation.version)
        print(f"{device.implementation.name} {version_str} - {device.implementation.platform}")
