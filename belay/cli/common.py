from pathlib import Path
from typing import Union

import tomli

help_port = "Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."
help_password = (  # nosec
    "Password for communication methods (like WebREPL) that require authentication."
)


def load_toml(path: Union[str, Path] = "pyproject.toml"):
    """Load a TOML file.

    If the specified toml file is not found, parent directories
    are iteratively searched until a toml file is found.
    """
    path = Path(path).absolute()

    for parent in path.parents:
        candidate = parent / path.name
        try:
            with candidate.open("rb") as f:
                toml = tomli.load(f)
            break
        except FileNotFoundError:
            pass
    else:
        raise FileNotFoundError

    try:
        toml = toml["tool"]["belay"]
    except KeyError:
        return {}

    return toml
