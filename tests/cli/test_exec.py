from belay.cli.main import app
from tests.conftest import run_cli


def test_exec_basic(mocker, mock_device):
    mock_device.patch("belay.cli.exec.Device")
    exit_code = run_cli(app, ["exec", "/dev/ttyUSB0", "print('hello world')", "--password", "password"])
    assert exit_code == 0
    mock_device.cls_assert_common()
    mock_device.inst.assert_called_once_with("print('hello world')")
