from belay import Device
from belay.cli.common import PasswordStr, PortStr


def info(port: PortStr, *, password: PasswordStr = ""):
    """Display device firmware information."""
    device = Device(port, password=password)
    version_str = "v" + ".".join(str(x) for x in device.implementation.version)
    print(f"{device.implementation.name} {version_str} - {device.implementation.platform}")
    device.close()
