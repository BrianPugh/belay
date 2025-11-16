from functools import partial
from pathlib import Path
from typing import Optional

from rich.progress import Progress

from belay import Device
from belay.cli.common import PasswordStr, PortStr


def sync_device(device, folder, progress_update, **kwargs):
    device.sync(folder, progress_update=progress_update, **kwargs)
    progress_update(description="Complete.")


def sync(
    port: PortStr,
    folder: Path,
    *,
    dst: str = "/",
    password: PasswordStr = "",
    keep: Optional[list[str]] = None,
    ignore: Optional[list[str]] = None,
    mpy_cross_binary: Optional[Path] = None,
):
    """Synchronize a folder to device.

    Parameters
    ----------
    folder : Path
        Path of local file or folder to sync.
    dst : str
        Destination directory to unpack folder contents to.
    keep : Optional[list[str]]
        Files to keep.
    ignore : Optional[list[str]]
        Files to ignore.
    mpy_cross_binary : Optional[Path]
        Compile py files with this executable.
    """
    with Device(port, password=password) as device, Progress() as progress:
        task_id = progress.add_task("")

        def progress_update(description=None, **kwargs):
            return progress.update(task_id, description=description, **kwargs)

        sync_device(
            device,
            folder,
            progress_update,
            dst=dst,
            keep=keep,
            ignore=ignore,
            mpy_cross_binary=mpy_cross_binary,
        )
