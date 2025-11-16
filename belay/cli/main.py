import os
import shutil
import subprocess  # nosec
import sys
from tempfile import TemporaryDirectory
from typing import Annotated

from cyclopts import App, Parameter

import belay
from belay.cli.cache import app as cache_app
from belay.cli.clean import clean
from belay.cli.exec import exec
from belay.cli.info import info
from belay.cli.install import install
from belay.cli.new import new
from belay.cli.run import run
from belay.cli.select import select
from belay.cli.sync import sync
from belay.cli.terminal import terminal
from belay.cli.update import update
from belay.project import load_groups

app = App(version_flags=("--version", "-v"), help_format="markdown")
app.command(cache_app, name="cache")
app.command(clean)
app.command(exec)
app.command(info)
app.command(install)
app.command(new)
app.command(run)
app.command(select)
app.command(sync)
app.command(terminal)
app.command(update)


def run_exec(command: list[str]):
    """Enable virtual-environment and run command."""
    groups = load_groups()
    virtual_env = os.environ.copy()
    # Add all dependency groups to the micropython path.
    # This flattens all dependencies to a single folder and fetches fresh
    # copies of dependencies in `develop` mode.
    with TemporaryDirectory() as tmp_dir:
        virtual_env["MICROPYPATH"] = f".:{tmp_dir}"
        for group in groups:
            group.copy_to(tmp_dir)

        try:
            subprocess.run(  # nosec
                command,
                env=virtual_env,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)


def _get(indexable, index, default=None):
    try:
        return indexable[index]
    except IndexError:
        return default


def run_app(*args, **kwargs):
    """Add CLI hacks that are not Cyclopts-friendly here."""
    command = _get(sys.argv, 1)
    if command == "run":
        try:
            exec_path = shutil.which(sys.argv[2])
        except IndexError:
            exec_path = None
        if exec_path is not None:
            run_exec(sys.argv[2:])
        else:
            app(*args, **kwargs)
    else:
        # Common-case; use Cyclopts functionality.
        app(*args, **kwargs)
