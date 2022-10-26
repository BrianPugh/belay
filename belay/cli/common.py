from pathlib import Path
from typing import Union

import tomli

help_port = "Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."
help_password = (  # nosec
    "Password for communication methods (like WebREPL) that require authentication."
)


def load_toml(path: Union[str, Path] = "pyproject.toml"):
    path = Path(path)

    with path.open("rb") as f:
        toml = tomli.load(f)

    try:
        toml = toml["tool"]["belay"]
    except KeyError:
        return {}

    return toml
