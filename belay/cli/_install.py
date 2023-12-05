import shutil
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

from cyclopts import Parameter
from rich.progress import Progress
from typing_extensions import Annotated

from belay import Device
from belay.cli._sync import sync_device as _sync_device
from belay.cli.common import remove_stacktrace
from belay.cli.main import app
from belay.project import find_project_folder, load_groups, load_pyproject


@app.command
def install(
    port: str,
    *,
    password: Optional[str] = None,
    mpy_cross_binary: Optional[Path] = None,
    run: Optional[Path] = None,
    main: Optional[Path] = None,
    with_groups: Annotated[Optional[List[str]], Parameter(name="--with")] = None,
    follow: Annotated[bool, Parameter(name=["--follow", "-f"])] = False,
):
    """Sync dependencies and project itself to device.

    Parameters
    ----------
    port: str
        Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device.
    password: Optional[str]
        Password for communication methods (like WebREPL) that require authentication.
    mpy_cross_binary: Optional[Path]
        Compile py files with this executable.
    run: Optional[Path]
        Run script on-device after installing.
    main: Optional[Path]
        Sync script to /main.py after installing.
    with_groups: List[str]
        Include specified optional dependency group.
    follow: bool
        Follow the stdout after upload.
    """
    kwargs = {}
    if run and run.suffix != ".py":
        raise ValueError("Run script MUST be a python file.")
    if main and main.suffix != ".py":
        raise ValueError("Main script MUST be a python file.")
    if with_groups is None:
        with_groups = []
    if password is not None:
        kwargs["password"] = password

    config = load_pyproject()
    project_folder = find_project_folder()
    project_package = config.name
    groups = load_groups()

    with Device(port, **kwargs) as device:
        sync_device = partial(
            _sync_device,
            device,
            mpy_cross_binary=mpy_cross_binary,
        )

        with TemporaryDirectory() as tmp_dir, Progress() as progress:
            tmp_dir = Path(tmp_dir)

            # Add all tasks to progress bar
            tasks = {}

            def create_task(key, task_description):
                task_id = progress.add_task(task_description)

                def progress_update(description=None, **kwargs):
                    if description:
                        description = task_description + description
                    progress.update(task_id, description=description, **kwargs)

                tasks[key] = progress_update

            create_task("dependencies", "Dependencies: ")
            if project_package:
                create_task("project_package", f"{project_package}: ")
            if main:
                create_task("main", "main: ")

            # Aggregate dependencies to an intermediate temporary directory.
            for group in groups:
                if group.optional and group.name not in with_groups:
                    continue
                group.copy_to(tmp_dir)

            sync_device(
                tmp_dir,
                dst="/lib",
                progress_update=tasks["dependencies"],
            )

            if project_package:
                sync_device(
                    folder=project_folder / project_package,
                    dst=f"/{project_package}",
                    progress_update=tasks["project_package"],
                    ignore=config.ignore,
                )

            if main:
                # Copy provided main to temporary directory in case it's not named main.py
                main_tmp = tmp_dir / "main.py"
                shutil.copy(main, main_tmp)
                sync_device(main_tmp, progress_update=tasks["main"])

        if run:
            content = run.read_text()
            with remove_stacktrace():
                device(content)
            return

        # Reset device so ``main.py`` has a chance to execute.
        device.soft_reset()
        if follow:
            device.terminal()
