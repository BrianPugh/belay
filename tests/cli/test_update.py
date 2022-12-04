import os

from typer.testing import CliRunner

import belay
import belay.cli.common
from belay.cli import app

cli_runner = CliRunner()


def test_update(mocker, tmp_path):
    os.chdir(tmp_path)

    toml_path = tmp_path / "pyproject.toml"
    toml_path.touch()
    belay_path = tmp_path / ".belay"

    dependency_groups = {
        "main": {
            "foo": "foo.py",
        }
    }
    mock_load_toml = mocker.patch(
        "belay.cli.update.load_dependency_groups", return_value=dependency_groups
    )
    mock_download_dependencies = mocker.patch("belay.cli.update.download_dependencies")
    res = cli_runner.invoke(app, ["update"])
    assert res.exit_code == 0
    mock_load_toml.assert_called_once_with()
    mock_download_dependencies.assert_called_once_with(
        {"foo": "foo.py"},
        belay_path / "dependencies" / "main",
        packages=[],
        console=mocker.ANY,
    )
