from pathlib import Path
from typing import Optional, Union

import tomli
from rich.console import Console
from typer import Option

from belay.packagemanager import download_dependencies


def _load_toml(path: Union[str, Path]):
    path = Path(path)

    with path.open("rb") as f:
        toml = tomli.load(f)

    try:
        toml = toml["tool"]["belay"]
    except KeyError:
        return {}

    return toml


def update(package: Optional[str] = Option(None)):
    console = Console()

    toml = _load_toml("pyproject.toml")

    try:
        dependencies = toml["dependencies"]
    except KeyError:
        return

    download_dependencies(dependencies, package=package, console=console)
