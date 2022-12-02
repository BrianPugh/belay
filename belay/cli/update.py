from typing import List

from rich.console import Console
from typer import Argument

from belay.packagemanager import clean_local, download_dependencies

from .common import find_dependencies_folder, load_dependency_groups, load_pyproject


def update(packages: List[str] = Argument(None, help="Specific package(s) to update.")):
    """Download new versions of dependencies."""
    console = Console()
    dependency_groups = load_dependency_groups()

    for name, dependencies in dependency_groups.items():
        directory = find_dependencies_folder() / name
        download_dependencies(
            dependencies,
            directory,
            packages=packages,
            console=console,
        )
        clean_local(dependencies.keys(), directory)
