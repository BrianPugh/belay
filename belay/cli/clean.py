from belay.packagemanager import clean_local

from .common import load_toml


def clean():
    """Remove any downloaded dependencies if they are no longer specified in pyproject."""
    toml = load_toml()

    try:
        dependencies = toml["dependencies"]
    except KeyError:
        return

    clean_local(dependencies.keys())
