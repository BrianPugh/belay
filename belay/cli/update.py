from typing import List

from rich.console import Console
from typer import Argument

from belay.cli.clean import clean
from belay.project import load_groups


def update(packages: List[str] = Argument(None, help="Specific package(s) to update.")):
    """Download new versions of dependencies."""
    console = Console()
    groups = load_groups()
    packages = packages if packages else None

    for group in groups:
        if packages is None:
            group_packages = None
        else:
            group_packages = [x for x in packages if x in group.config.dependencies]

        group.download(
            packages=group_packages,
            console=console,
        )

    clean()
