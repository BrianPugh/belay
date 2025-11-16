from pathlib import Path

from belay import Device
from belay.cli.common import PasswordStr, PortStr, remove_stacktrace


def run(port: PortStr, file: Path, *, password: PasswordStr = ""):
    """Run file on-device.

    If the first argument, `port`, is resolvable to an executable,
    the remainder of the command will be interpreted as a shell command
    that will be executed in a pseudo-micropython-virtual-environment.
    As of right now, this just sets `MICROPYPATH` to all of the dependency
    groups' folders. E.g:

    ```bash
    belay run micropython -m unittest
    ```

    Parameters
    ----------
    file : Path
        File to run on-device.
    """
    content = file.read_text(encoding="utf-8")
    with Device(port, password=password) as device, remove_stacktrace():
        device(content)
