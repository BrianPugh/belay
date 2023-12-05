from pathlib import Path
from typing import List, Optional

from rich.progress import Progress

from belay import Device
from belay.cli.main import app


def sync_device(device, folder, progress_update, **kwargs):
    device.sync(folder, progress_update=progress_update, **kwargs)
    progress_update(description="Complete.")


@app.command
def sync(
    port: str,
    folder: Path,
    dst: str = "/",
    *,
    password: Optional[str] = None,
    keep: Optional[List[str]] = None,
    ignore: Optional[List[str]] = None,
    mpy_cross_binary: Optional[Path] = None,
):
    """Synchronize a folder to device.

    Parameters
    ----------
    port: str
        Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device.
    folder: Path
        Path of local file or folder to sync.
    dst: str
        Destination directory to unpack folder contents to.
    mpy_cross_binary: Optional[Path]
        Compile py files with this executable.
    keep: Optional[List[str]]
        Files to keep.
    ignore: Optional[List[str]]
        Files to ignore.
    password: Optional[str]
        Password for communication methods (like WebREPL) that require authentication.
    """
    kwargs = {}
    if password is not None:
        kwargs["password"] = password

    with Device(port, **kwargs) as device, Progress() as progress:
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
