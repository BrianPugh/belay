import os

from belay.cli import app
from belay.packagemanager import Group


def test_update(mocker, tmp_path):
    os.chdir(tmp_path)

    toml_path = tmp_path / "pyproject.toml"
    toml_path.touch()

    groups = [Group("name", dependencies={"foo": "foo.py"})]
    mock_download = mocker.patch.object(groups[0], "download")
    mock_load_groups = mocker.patch("belay.cli._update.load_groups", return_value=groups)
    assert not app("update")
    mock_load_groups.assert_called_once_with()
    mock_download.assert_called_once_with(
        packages=None,
        console=mocker.ANY,
    )


def test_update_specific_packages(mocker, tmp_path):
    os.chdir(tmp_path)

    toml_path = tmp_path / "pyproject.toml"
    toml_path.touch()

    groups = [Group("name", dependencies={"foo": "foo.py", "bar": "bar.py", "baz": "baz.py"})]
    mock_download = mocker.patch.object(groups[0], "download")
    mock_load_groups = mocker.patch("belay.cli._update.load_groups", return_value=groups)
    assert not app(["update", "bar", "baz"])
    mock_load_groups.assert_called_once_with()
    mock_download.assert_called_once_with(
        packages=["bar", "baz"],
        console=mocker.ANY,
    )
