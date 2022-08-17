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


class SingleTaskProgress(Progress):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, console=console, **kwargs)
        self.last_task_id = self.add_task("")

    def update(self, *args, **kwargs):
        return super().update(task_id=self.last_task_id, *args, **kwargs)


@app.callback()
def callback(silent: bool = False):
    """Tool to interact with MicroPython hardware."""
    global console
    state["silent"] = silent
    console_kwargs = {}
    if state["silent"]:
        console_kwargs["quiet"] = True
    console = Console(**console_kwargs)


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
    with SingleTaskProgress() as progress:
        progress.update(description=f"Connecting to {port}")
        device = belay.Device(port, password=password)
        progress.update(description=f"Connected to {port}.")

        device.sync(folder, progress=progress)

        progress.update(description="Sync complete.")


def main():
    app()
