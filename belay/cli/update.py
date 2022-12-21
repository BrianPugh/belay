from typing import List

from rich.console import Console
from typer import Argument

from belay.project import load_groups


def update(packages: List[str] = Argument(None, help="Specific package(s) to update.")):
    """Download new versions of dependencies."""
    console = Console()
    groups = load_groups()
    packages = packages if packages else None

    for group in groups:
        group.download(
            packages=packages,
            console=console,
        )
        group.clean()
