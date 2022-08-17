from functools import partial
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress
from typer import Argument, Option

import belay

Arg = partial(Argument, ..., show_default=False)
Opt = partial(Option)

app = typer.Typer()
state = {}
console: Console


@app.callback()
def callback(silent: bool = False):
    """Tool to interact with MicroPython hardware."""
    global console, Progress
    state["silent"] = silent
    console_kwargs = {}
    if state["silent"]:
        console_kwargs["quiet"] = True
    console = Console(**console_kwargs)
    Progress = partial(Progress, console=console)


@app.command()
def sync(
    port: str = Arg(
        help="Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."
    ),
    folder: Path = Arg(help="Path to folder to sync."),
    password: str = Opt(
        "",
        help="Password for communication methods (like WebREPL) that require authentication.",
    ),
):
    """Synchronize a folder to device."""
    with Progress() as progress:
        task_id = progress.add_task("")
        progress_update = partial(progress.update, task_id)
        progress_update(description=f"Connecting to {port}")
        device = belay.Device(port, password=password)
        progress_update(description=f"Connected to {port}.")

        device.sync(folder, progress_update=progress_update)

        progress_update(description="Sync complete.")
