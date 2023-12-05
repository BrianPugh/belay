from pathlib import Path
from typing import Optional

from belay import Device
from belay.cli.common import remove_stacktrace
from belay.cli.main import app


@app.command
def run(
    port: str,
    file: Path,
    *,
    password: Optional[str] = None,
):
    """Run file on-device.

    If the first argument, ``port``, is resolvable to an executable,
    the remainder of the command will be interpreted as a shell command
    that will be executed in a pseudo-micropython-virtual-environment.
    As of right now, this just sets ``MICROPYPATH`` to all of the dependency
    groups' folders.

    .. code-block:: console

        $ belay run micropython -m unittest

    Parameters
    ----------
    port: str
        Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device.
    file: Path
        File to run on-device.
    password: Optional[str]
        Password for communication methods (like WebREPL) that require authentication.
    """
    kwargs = {}
    if password is not None:
        kwargs["password"] = password

    content = file.read_text()
    with Device(port, **kwargs) as device, remove_stacktrace():
        device(content)
