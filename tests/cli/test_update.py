from typer.testing import CliRunner

from belay.cli import app

cli_runner = CliRunner()


def test_update(mocker):
    belay_toml = {
        "dependencies": {
            "foo": "foo.py",
        }
    }
    mock_load_toml = mocker.patch("belay.cli.update.load_toml", return_value=belay_toml)
    mock_download_dependencies = mocker.patch("belay.cli.update.download_dependencies")
    res = cli_runner.invoke(app, ["update"])
    assert res.exit_code == 0
    mock_load_toml.assert_called_once_with()
    mock_download_dependencies.assert_called_once_with(
        {"foo": "foo.py"}, package=None, console=mocker.ANY
    )
