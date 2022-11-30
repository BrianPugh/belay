from pathlib import Path

from typer.testing import CliRunner

from belay.cli import app

cli_runner = CliRunner()


def test_install_basic(mocker):
    toml = {"name": "my_pkg_name"}
    mock_load_toml = mocker.patch("belay.cli.install.load_toml", return_value=toml)
    mock_sync = mocker.patch("belay.cli.install.sync")
    mock_run = mocker.patch("belay.cli.install.run_cmd")

    result = cli_runner.invoke(
        app, ["install", "/dev/ttyUSB0", "--password", "password", "--run", "main.py"]
    )

    assert result.exit_code == 0
    mock_load_toml.assert_called_once()
    assert mock_sync.call_args_list == [
        mocker.call(
            port="/dev/ttyUSB0",
            folder=Path(".belay/dependencies/main"),
            dst="/lib",
            password="password",
            keep=None,
            ignore=None,
            mpy_cross_binary=None,
        ),
        mocker.call(
            port="/dev/ttyUSB0",
            folder=Path("my_pkg_name"),
            dst="/my_pkg_name",
            password="password",
            keep=None,
            ignore=None,
            mpy_cross_binary=None,
        ),
    ]

    mock_run.assert_called_once_with(
        port="/dev/ttyUSB0", password="password", file=Path("main.py")
    )
