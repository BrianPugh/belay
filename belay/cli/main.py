import os
import shutil
import subprocess  # nosec
import sys
from tempfile import TemporaryDirectory
from typing import List

from cyclopts import App

app = App()


def run_exec(command: List[str]):
    """Enable virtual-environment and run command."""
    from belay.project import load_groups

    groups = load_groups()
    virtual_env = os.environ.copy()
    # Add all dependency groups to the micropython path.
    # This flattens all dependencies to a single folder and fetches fresh
    # copies of dependencies in ``develop`` mode.
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


def run_app():
    try:
        command = sys.argv[1]
    except IndexError:
        command = None

    try:
        exec_path = shutil.which(sys.argv[2])
    except IndexError:
        exec_path = None

    if command == "run" and exec_path:
        # Special virtual-environment subprocess.
        run_exec(sys.argv[2:])
    else:
        # Common-case
        sys.exit(app())
