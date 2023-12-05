import builtins
import contextlib
import shutil

import questionary
from cyclopts import App, Parameter
from typing_extensions import Annotated

with contextlib.suppress(ImportError):
    import readline

from belay.cli.main import app
from belay.project import find_cache_folder

app.command(cache_app := App(name="cache", help="Perform action's on Belay's cache."))


@cache_app.command()
def clear(
    prefix: str = "",
    *,
    yes: Annotated[bool, Parameter(name=["--yes", "-y"])] = False,
    all_: Annotated[bool, Parameter(name=["--all", "-a"])] = False,
):
    """Clear cache.

    Parameters
    ----------
    prefix: str
        Clear all caches that start with this.
    yes: bool
        Skip interactive prompts confirming clear action.
    all_: bool
        Clear all caches.
    """
    if (not prefix and not all_) or (prefix and all_):
        print('Either provide a prefix OR set the "--all" flag.')
        return 1

    cache_folder = find_cache_folder()

    prefix += "*"
    cache_paths = builtins.list(cache_folder.glob(prefix))
    cache_names = [x.name for x in cache_paths]

    if not cache_paths:
        print(f'No caches found starting with "{prefix}"')
        return 0

    if not yes:
        print("Found caches:")
        for cache_name in cache_names:
            print(f"  • {cache_name}")
        confirmed = questionary.confirm("Clear these caches?").ask()
        if not confirmed:
            return 0

    for path in cache_paths:
        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)


@cache_app.command()
def list():
    """List cache elements."""
    cache_folder = find_cache_folder()
    items = [x.name for x in cache_folder.glob("*")]

    for item in items:
        print(item)


@cache_app.command()
def info():
    """Display cache location and size."""
    cache_folder = find_cache_folder()

    print(f"Location: {cache_folder}")

    n_elements = len(builtins.list(cache_folder.glob("*")))
    print(f"Elements: {n_elements}")

    size_in_bytes = sum(f.stat().st_size for f in cache_folder.glob("**/*") if f.is_file())
    size_in_megabytes = size_in_bytes / (1 << 20)
    print(f"Total Size: {size_in_megabytes:0.3}MB")
