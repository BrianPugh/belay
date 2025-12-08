from belay.cli.main import app
from belay.packagemanager import Group
from tests.conftest import run_cli


def test_update(mocker, tmp_cwd):
    (tmp_cwd / "pyproject.toml").touch()

    groups = [Group("name", dependencies={"foo": "foo.py"})]
    mock_download = mocker.patch.object(groups[0], "download")
    mock_load_groups = mocker.patch("belay.cli.update.load_groups", return_value=groups)

    exit_code = run_cli(app, ["update"])
    assert exit_code == 0

    mock_load_groups.assert_called_once_with()
    mock_download.assert_called_once_with(
        packages=None,
        console=mocker.ANY,
    )


def test_update_specific_packages(mocker, tmp_cwd):
    (tmp_cwd / "pyproject.toml").touch()

    groups = [Group("name", dependencies={"foo": "foo.py", "bar": "bar.py", "baz": "baz.py"})]
    mock_download = mocker.patch.object(groups[0], "download")
    mock_load_groups = mocker.patch("belay.cli.update.load_groups", return_value=groups)

    exit_code = run_cli(app, ["update", "bar", "baz"])
    assert exit_code == 0

    mock_load_groups.assert_called_once_with()
    mock_download.assert_called_once_with(
        packages=["bar", "baz"],
        console=mocker.ANY,
    )
