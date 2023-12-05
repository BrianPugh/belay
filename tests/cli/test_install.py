from pathlib import Path

from belay.cli import app


def test_install_no_pkg(tmp_path, mocker, mock_device):
    toml = {}
    main_py = tmp_path / "main.py"
    main_py.write_text("foo = 1")

    mock_load_toml = mocker.patch("belay.project.load_toml", return_value=toml)
    mock_device.patch("belay.cli._install.Device")

    assert not app(
        [
            "install",
            "/dev/ttyUSB0",
            "--password",
            "password",
            "--run",
            str(main_py),
        ]
    )

    mock_load_toml.assert_called_once()
    mock_device.cls.assert_called_once_with("/dev/ttyUSB0", password="password")
    mock_device.inst.sync.assert_called_once_with(  # Dependencies sync
        mocker.ANY,
        progress_update=mocker.ANY,
        mpy_cross_binary=None,
        dst="/lib",
    )

    mock_device.inst.assert_called_once_with("foo = 1")


def test_install_basic(tmp_path, mocker, mock_device):
    dependencies_folder = tmp_path / ".belay" / "dependencies"

    toml = {"name": "my_pkg_name"}

    mock_load_toml = mocker.patch("belay.project.load_toml", return_value=toml)
    mocker.patch("belay.project.find_dependencies_folder", return_value=dependencies_folder)
    mocker.patch("belay.cli._install.find_project_folder", return_value=Path())
    mock_device.patch("belay.cli._install.Device")

    assert not app(["install", "/dev/ttyUSB0", "--password", "password"])

    mock_load_toml.assert_called_once()
    mock_device.cls.assert_called_once_with("/dev/ttyUSB0", password="password")
    mock_device.inst.sync.assert_has_calls(
        [
            mocker.call(
                mocker.ANY,
                progress_update=mocker.ANY,
                mpy_cross_binary=None,
                dst="/lib",
            ),
            mocker.call(
                mocker.ANY,
                progress_update=mocker.ANY,
                mpy_cross_binary=None,
                dst="/my_pkg_name",
                ignore=[],
            ),
        ]
    )
