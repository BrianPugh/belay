from typing import Optional

from rich.console import Console
from typer import Option

from belay.packagemanager import download_dependencies

from .common import load_toml


def update(package: Optional[str] = Option(None)):
    console = Console()

    toml = load_toml()

    try:
        dependencies = toml["dependencies"]
    except KeyError:
        return

    download_dependencies(dependencies, package=package, console=console)
