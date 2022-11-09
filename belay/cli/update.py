from typing import List

from rich.console import Console
from typer import Argument

from belay.packagemanager import clean_local, download_dependencies

from .common import load_toml


def update(packages: List[str] = Argument(None, help="Specific package(s) to update.")):
    """Download new versions of dependencies."""
    console = Console()
    toml = load_toml()

    try:
        dependencies = toml["dependencies"]
    except KeyError:
        return

    download_dependencies(dependencies, packages=packages, console=console)

    clean_local(dependencies.keys())
