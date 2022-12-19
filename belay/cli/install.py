import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

from rich.progress import Progress
from typer import Argument, Option

from belay import Device
from belay.cli.common import (
    find_dependencies_folder,
    help_password,
    help_port,
    load_pyproject,
)
from belay.cli.run import run as run_cmd
from belay.cli.sync import sync


def install(
    port: str = Argument(..., help=help_port),
    password: str = Option("", help=help_password),
    mpy_cross_binary: Optional[Path] = Option(
        None, help="Compile py files with this executable."
    ),
    run: Optional[Path] = Option(None, help="Run script on-device after installing."),
    main: Optional[Path] = Option(
        None, help="Sync script to /main.py after installing."
    ),
):
    """Sync dependencies and project itself to device."""
    if run and run.suffix != ".py":
        raise ValueError("Run script MUST be a python file.")
    if main and main.suffix != ".py":
        raise ValueError("Main script MUST be a python file.")

    toml = load_pyproject()
    pkg_name = toml.get("name")
    dependency_folder = find_dependencies_folder()

    with TemporaryDirectory() as tmp_dir:
        # Aggregate dependencies to an intermediate temporary directory.
        tmp_dir = Path(tmp_dir)

        # TODO: better to get what groups to install from the cli.
        #       If not specified, all non-optional groups will be installed.
        for group_folder in dependency_folder.glob("*/"):
            shutil.copytree(group_folder, tmp_dir, dirs_exist_ok=True)

        sync(
            port=port,
            folder=tmp_dir,
            dst="/lib",
            password=password,
            keep=None,
            ignore=None,
            mpy_cross_binary=mpy_cross_binary,
        )

    if pkg_name:
        sync(
            port=port,
            folder=Path(pkg_name),
            dst=f"/{pkg_name}",
            password=password,
            keep=None,
            ignore=None,
            mpy_cross_binary=mpy_cross_binary,
        )

    if main:
        with Device(port, password=password) as device:
            device.sync(main, keep=True, mpy_cross_binary=mpy_cross_binary)

    if run:
        run_cmd(port=port, file=run, password=password)
