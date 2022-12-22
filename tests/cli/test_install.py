from pathlib import Path

from typer.testing import CliRunner

from belay.cli import app

cli_runner = CliRunner()


def test_install_no_pkg(mocker):
    toml = {}

    mocker.patch("belay.project.load_pyproject", return_value=toml)
    mock_load_toml = mocker.patch("belay.cli.install.load_pyproject", return_value=toml)
    mock_sync = mocker.patch("belay.cli.install.sync")
    mock_run = mocker.patch("belay.cli.install.run_cmd")

    result = cli_runner.invoke(
        app, ["install", "/dev/ttyUSB0", "--password", "password", "--run", "main.py"]
    )

    assert result.exit_code == 0
    mock_load_toml.assert_called_once()
    mock_sync.assert_called_once_with(
        port="/dev/ttyUSB0",
        folder=mocker.ANY,
        dst="/lib",
        password="password",
        keep=None,
        ignore=None,
        mpy_cross_binary=None,
    )

    mock_run.assert_called_once_with(
        port="/dev/ttyUSB0", password="password", file=Path("main.py")
    )


def test_install_basic(tmp_path, mocker):
    dependencies_folder = tmp_path / ".belay" / "dependencies"

    toml = {"name": "my_pkg_name"}

    mocker.patch("belay.project.load_pyproject", return_value=toml)
    mock_load_toml = mocker.patch("belay.cli.install.load_pyproject", return_value=toml)
    mocker.patch(
        "belay.project.find_dependencies_folder", return_value=dependencies_folder
    )
    mocker.patch("belay.cli.install.find_project_folder", return_value=Path())
    mock_sync = mocker.patch("belay.cli.install.sync")

    result = cli_runner.invoke(
        app, ["install", "/dev/ttyUSB0", "--password", "password"]
    )

    assert result.exit_code == 0
    mock_load_toml.assert_called_once()
    mock_sync.assert_any_call(
        port="/dev/ttyUSB0",
        folder=mocker.ANY,
        dst="/lib",
        password="password",
        keep=None,
        ignore=None,
        mpy_cross_binary=None,
    )
    mock_sync.assert_any_call(
        port="/dev/ttyUSB0",
        folder=Path("my_pkg_name"),
        dst="/my_pkg_name",
        password="password",
        keep=None,
        ignore=None,
        mpy_cross_binary=None,
    )
