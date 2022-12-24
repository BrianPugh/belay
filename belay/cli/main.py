import os
import subprocess  # nosec
import sys
from typing import List

import typer

from belay import Device
from belay.cli.clean import clean
from belay.cli.common import help_password, help_port
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
    subprocess.run(  # nosec
        command,
        env=virtual_env,
        check=True,
    )


def run_app(*args, **kwargs):
    """Add CLI hacks that are not Typer-friendly here."""
    exec_identifier = "exec:"
    if sys.argv[1] == "run" and sys.argv[2].startswith(exec_identifier):
        # See docstring in belay.cli.run.run
        command = sys.argv[2:].copy()
        command[0] = command[0][len(exec_identifier) :]
        if not command[0]:
            command = command[1:]
        run_exec(command)
    else:
        # Common-case; use Typer functionality.
        app(*args, **kwargs)
