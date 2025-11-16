from pathlib import Path

from belay.cli.main import app
from tests.conftest import run_cli


def test_sync_basic(mocker, mock_device):
    mock_device.patch("belay.cli.sync.Device")
    exit_code = run_cli(app, ["sync", "/dev/ttyUSB0", "foo", "--password", "password"])
    assert exit_code == 0
    mock_device.cls_assert_common()
    mock_device.inst.sync.assert_called_once_with(
        Path("foo"),
        dst="/",
        keep=None,
        ignore=None,
        mpy_cross_binary=None,
        progress_update=mocker.ANY,
    )
