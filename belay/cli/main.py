import os
import shutil
import subprocess  # nosec
import sys
from tempfile import TemporaryDirectory
from typing import List

import typer
from typer import Option

import belay
from belay.cli import cache
from belay.cli.clean import clean
from belay.cli.exec import exec
from belay.cli.identify import identify
from belay.cli.info import info
from belay.cli.install import install
from belay.cli.new import new
from belay.cli.run import run
from belay.cli.sync import sync
from belay.cli.update import update
from belay.project import load_groups

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
app.add_typer(cache.app, name="cache")

app.command()(clean)
app.command()(exec)
app.command()(identify)
app.command()(info)
app.command()(install)
app.command()(new)
app.command()(run)
app.command()(sync)
app.command()(update)


def run_exec(command: List[str]):
    """Pseudo-virtual-environment."""
    groups = load_groups()
    virtual_env = os.environ.copy()
    # Add all dependency groups to the micropython path.
    with TemporaryDirectory() as tmp_dir:
        virtual_env["MICROPYPATH"] = tmp_dir
        for group in groups:
            group.copy_to(tmp_dir)

        return subprocess.run(  # nosec
            command,
            env=virtual_env,
            check=True,
        ).returncode


def _get(indexable, index, default=None):
    try:
        return indexable[index]
    except IndexError:
        return default


def run_app(*args, **kwargs):
    """Add CLI hacks that are not Typer-friendly here."""
    command = _get(sys.argv, 1)

    try:
        exec_path = shutil.which(sys.argv[2])
    except IndexError:
        exec_path = None

    if command == "run" and exec_path:
        # See docstring in belay.cli.run.run
        return run_exec(sys.argv[2:])

    # Common-case; use Typer functionality.
    app(*args, **kwargs)


def version_callback(value: bool):
    if not value:
        return
    print(belay.__version__)
    raise typer.Exit()


@app.callback()
def common(
    ctx: typer.Context,
    version: bool = Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        help="Display Belay's version.",
    ),
):
    pass
