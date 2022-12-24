import os
import shutil
import subprocess  # nosec
import sys
from typing import List

import typer

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

app = typer.Typer()
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
    virtual_env["MICROPYPATH"] = os.pathsep.join(str(g.folder) for g in groups)
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
