from belay.packagemanager import clean_local

from .common import find_dependencies_folder, load_dependency_groups


def clean():
    """Remove any downloaded dependencies if they are no longer specified in pyproject."""
    dependency_groups = load_dependency_groups()

    for name, dependencies in dependency_groups.items():
        directory = find_dependencies_folder() / name
        clean_local(dependencies.keys(), directory)
