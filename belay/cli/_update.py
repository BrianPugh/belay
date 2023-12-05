from rich.console import Console

from belay.cli._clean import clean
from belay.cli.main import app
from belay.project import load_groups


@app.command
def update(*packages: str):
    """Download new versions of dependencies.

    Parameters
    ----------
    packages: Optional[List[str]]
        Specific package(s) to update.
        Defaults to all packages.
    """
    console = Console()
    groups = load_groups()

    for group in groups:
        group_packages = [x for x in packages if x in group.config.dependencies] if packages else None

        group.download(
            packages=group_packages,
            console=console,
        )

    clean()
