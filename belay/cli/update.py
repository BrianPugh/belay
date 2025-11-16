from rich.console import Console

from belay.cli.clean import clean
from belay.project import load_groups


def update(*packages: str):
    """Download new versions of dependencies.

    Parameters
    ----------
    *packages : str
        Specific package(s) to update.
    """
    console = Console()
    groups = load_groups()
    packages = packages if packages else None

    for group in groups:
        group_packages = None if packages is None else [x for x in packages if x in group.config.dependencies]

        group.download(
            packages=group_packages,
            console=console,
        )

    clean()
