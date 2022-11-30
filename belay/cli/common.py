from pathlib import Path
from typing import Union

import tomli

help_port = "Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."
help_password = (  # nosec
    "Password for communication methods (like WebREPL) that require authentication."
)


def find_pyproject():
    path = Path("pyproject.toml").absolute()

    for parent in path.parents:
        candidate = parent / path.name
        if candidate.exists():
            return candidate
    raise FileNotFoundError


def load_toml(path: Union[str, Path]):
    path = Path(path)
    with path.open("rb") as f:
        toml = tomli.load(f)

    try:
        toml = toml["tool"]["belay"]
    except KeyError:
        return {}

    return toml


def load_pyproject():
    """Load the pyproject TOML file."""
    pyproject_path = find_pyproject()
    return load_toml(pyproject_path)
