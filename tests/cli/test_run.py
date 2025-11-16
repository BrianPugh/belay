from belay.cli.main import app
from tests.conftest import run_cli


def test_run_basic(mocker, mock_device, tmp_path):
    mock_device.patch("belay.cli.run.Device")
    py_file = tmp_path / "foo.py"
    py_file.write_text("print('hello')\nprint('world')")
    exit_code = run_cli(app, ["run", "/dev/ttyUSB0", str(py_file), "--password", "password"])
    assert exit_code == 0
    mock_device.cls_assert_common()
    mock_device.inst.assert_called_once_with("print('hello')\nprint('world')")
