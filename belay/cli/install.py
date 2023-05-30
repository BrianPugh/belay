import shutil
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

from rich.progress import Progress
from typer import Argument, Option

from belay import Device
from belay.cli.common import help_password, help_port, remove_stacktrace
from belay.cli.sync import sync_device as _sync_device
from belay.project import find_project_folder, load_groups, load_pyproject


def install(
    port: str = Argument(..., help=help_port),
    password: str = Option("", help=help_password),
    mpy_cross_binary: Optional[Path] = Option(None, help="Compile py files with this executable."),
    run: Optional[Path] = Option(None, help="Run script on-device after installing."),
    main: Optional[Path] = Option(None, help="Sync script to /main.py after installing."),
    with_groups: List[str] = Option(None, "--with", help="Include specified optional dependency group."),
    follow: bool = Option(False, "--follow", "-f", help="Follow the stdout after upload."),
):
    """Sync dependencies and project itself to device."""
    if run and run.suffix != ".py":
        raise ValueError("Run script MUST be a python file.")
    if main and main.suffix != ".py":
        raise ValueError("Main script MUST be a python file.")

    config = load_pyproject()
    project_folder = find_project_folder()
    project_package = config.name
    groups = load_groups()

    with Device(port, password=password) as device:
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
