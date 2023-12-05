from typing import Optional

from belay import Device
from belay.cli.common import remove_stacktrace
from belay.cli.main import app


@app.command
def exec(port: str, statement: str, *, password: Optional[str] = None):
    """Execute python statement on-device.

    Parameters
    ----------
    port: str
        Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device.
    statement: str
        Statement to execute on-device.
    password: Optional[str]
        Password for communication methods (like WebREPL) that require authentication.
    """
    kwargs = {}
    if password is not None:
        kwargs["password"] = password
    with Device(port, **kwargs) as device, remove_stacktrace():
        device(statement)
