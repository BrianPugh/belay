from belay import Device
from belay.cli.common import PasswordStr, PortStr


def terminal(port: PortStr, *, password: PasswordStr = ""):
    """Open up an interactive REPL.

    Press ctrl+] to exit.
    """
    with Device(port, password=password) as device:
        device.terminal()
