from pathlib import Path
from typing import List, Optional

from rich.progress import Progress
from typer import Argument, Option

from belay import Device
from belay.cli.common import help_password, help_port, load_toml
from belay.cli.run import run as run_cmd
from belay.cli.sync import sync


def install(
    port: str = Argument(..., help=help_port),
    password: str = Option("", help=help_password),
    mpy_cross_binary: Optional[Path] = Option(
        None, help="Compile py files with this executable."
    ),
    run: Optional[Path] = Option(None, help="Run script on-device after installing."),
):
    """Sync dependencies and project itself."""
    toml = load_toml()
    pkg_name = toml["name"]

    sync(
        port=port,
        folder=".belay-lib",
        dst="/lib",
        password=password,
        keep=None,
        ignore=None,
        mpy_cross_binary=mpy_cross_binary,
    )
    sync(
        port=port,
        folder=pkg_name,
        dst=f"/{pkg_name}",
        password=password,
        keep=None,
        ignore=None,
        mpy_cross_binary=mpy_cross_binary,
    )
    if run:
        run_cmd(port=port, file=run, password=password)
