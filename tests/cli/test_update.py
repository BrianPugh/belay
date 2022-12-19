import os

from typer.testing import CliRunner

from belay.cli import app
from belay.packagemanager import Group

cli_runner = CliRunner()


def test_update(mocker, tmp_path):
    os.chdir(tmp_path)

    toml_path = tmp_path / "pyproject.toml"
    toml_path.touch()

    groups = [Group("name", dependencies={"foo": "foo.py"})]
    mock_download_dependencies = mocker.patch.object(
        groups[0], "_download_dependencies"
    )
    mock_load_groups = mocker.patch("belay.cli.update.load_groups", return_value=groups)
    res = cli_runner.invoke(app, ["update"])
    assert res.exit_code == 0
    mock_load_groups.assert_called_once_with()
    mock_download_dependencies.assert_called_once_with(
        packages=None,
        console=mocker.ANY,
    )
