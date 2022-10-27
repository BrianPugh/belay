from typing import List

from rich.console import Console
from typer import Argument

from belay.packagemanager import download_dependencies

from .common import load_toml


def update(packages: List[str] = Argument(None, help="Specific package(s) to update.")):
    console = Console()
    toml = load_toml()

    try:
        dependencies = toml["dependencies"]
    except KeyError:
        return

    download_dependencies(dependencies, packages=packages, console=console)
