import typer

from belay import Device
from belay.cli.common import help_password, help_port
from belay.cli.exec import exec
from belay.cli.identify import identify
from belay.cli.info import info
from belay.cli.install import install
from belay.cli.run import run
from belay.cli.sync import sync
from belay.cli.update import update

app = typer.Typer()
app.command()(sync)
app.command()(run)
app.command()(exec)
app.command()(info)
app.command()(identify)
app.command()(update)
app.command()(install)
