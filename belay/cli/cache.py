import builtins
import contextlib

with contextlib.suppress(ImportError):
    import readline
import shutil
import sys
from typing import Annotated

from cyclopts import App, Parameter

from belay.project import find_cache_folder

app = App(help="Perform action's on Belay's cache.")


@app.command
def clear(
    prefix: str = "",
    *,
    yes: Annotated[bool, Parameter(alias="-y")] = False,
    all: Annotated[bool, Parameter(alias="-a")] = False,
):
    """Clear cache.

    Parameters
    ----------
    prefix : str
        Clear all caches that start with this.
    yes : bool
        Automatically answer "yes" to all confirmation prompts.
    all : bool
        Clear all caches.
    """
    if (not prefix and not all) or (prefix and all):
        print('Either provide a prefix OR set the "--all" flag.')
        sys.exit(1)

    cache_folder = find_cache_folder()

    prefix += "*"
    cache_paths = builtins.list(cache_folder.glob(prefix))
    cache_names = [x.name for x in cache_paths]

    if not cache_paths:
        print(f'No caches found starting with "{prefix}"')
        sys.exit(1)

    if not yes:
        print("Found caches:")
        for cache_name in cache_names:
            print(f"  • {cache_name}")
        response = input("Clear these caches? [y/N]: ")
        if response.lower() not in ("y", "yes"):
            sys.exit(1)

    for path in cache_paths:
        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)


@app.command
def list():
    """List cache elements."""
    cache_folder = find_cache_folder()
    items = [x.name for x in cache_folder.glob("*")]

    for item in items:
        print(item)


@app.command
def info():
    """Display cache location and size."""
    cache_folder = find_cache_folder()

    print(f"Location: {cache_folder}")

    n_elements = len(builtins.list(cache_folder.glob("*")))
    print(f"Elements: {n_elements}")

    size_in_bytes = sum(f.stat().st_size for f in cache_folder.glob("**/*") if f.is_file())
    size_in_megabytes = size_in_bytes / (1 << 20)
    print(f"Total Size: {size_in_megabytes:0.3}MB")
