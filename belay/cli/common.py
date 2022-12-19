from functools import lru_cache
from pathlib import Path
from typing import Union

import tomli

from ..exceptions import ConfigError

help_port = "Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."
help_password = (  # nosec
    "Password for communication methods (like WebREPL) that require authentication."
)


@lru_cache
def find_pyproject() -> Path:
    path = Path("pyproject.toml").absolute()

    for parent in path.parents:
        candidate = parent / path.name
        if candidate.exists():
            return candidate
    raise FileNotFoundError


@lru_cache
def find_belay_folder() -> Path:
    return find_pyproject().parent / ".belay"


@lru_cache
def find_dependencies_folder() -> Path:
    return find_belay_folder() / "dependencies"


@lru_cache
def load_toml(path: Union[str, Path]) -> dict:
    path = Path(path)
    with path.open("rb") as f:
        toml = tomli.load(f)

    try:
        toml = toml["tool"]["belay"]
    except KeyError:
        return {}

    return toml


@lru_cache
def load_pyproject() -> dict:
    """Load the pyproject TOML file."""
    pyproject_path = find_pyproject()
    return load_toml(pyproject_path)


@lru_cache
def load_dependency_groups():
    groups = {}

    config = load_pyproject()

    if "dependencies" in config:
        groups["main"] = config["dependencies"]

    for name, group_config in config.get("group", {}).items():
        if name == "main":
            raise ConfigError(
                'Specify "main" group dependencies under "tool.belay.dependencies", '
                'not "tool.belay.main.dependencies"'
            )

        if "dependencies" in group_config:
            groups[name] = group_config["dependencies"]

    return groups
