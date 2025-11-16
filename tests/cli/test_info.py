from belay.cli.main import app
from tests.conftest import run_cli


def test_info_basic(mocker, mock_device, capsys):
    mock_device.patch("belay.cli.info.Device")
    mock_device.inst.implementation.name = "testingpython"
    mock_device.inst.implementation.version = (4, 7, 9)
    mock_device.inst.implementation.platform = "pytest"
    exit_code = run_cli(app, ["info", "/dev/ttyUSB0", "--password", "password"])
    assert exit_code == 0
    mock_device.cls_assert_common()
    captured = capsys.readouterr()
    assert captured.out == "testingpython v4.7.9 - pytest\n"
