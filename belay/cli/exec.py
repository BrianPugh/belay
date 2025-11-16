from belay import Device
from belay.cli.common import PasswordStr, PortStr, remove_stacktrace


def exec(port: PortStr, statement: str, *, password: PasswordStr = ""):
    """Execute python statement on-device.

    Parameters
    ----------
    statement : str
        Statement to execute on-device.
    """
    device = Device(port, password=password)
    with remove_stacktrace():
        device(statement)
    device.close()
