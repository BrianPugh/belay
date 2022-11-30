from belay.packagemanager import clean_local

from .common import load_pyproject


def clean():
    """Remove any downloaded dependencies if they are no longer specified in pyproject."""
    toml = load_pyproject()

    try:
        dependencies = toml["dependencies"]
    except KeyError:
        return

    clean_local(dependencies.keys())
