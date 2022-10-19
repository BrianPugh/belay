from collections import namedtuple
from pathlib import PosixPath

import pytest
from typer.testing import CliRunner

from belay.cli import app

runner = CliRunner()
MockDevice = namedtuple("MockDevice", ["cls", "inst"])


@pytest.fixture
def mock_device(mocker):
    mock_instance = mocker.MagicMock()
    mock_class = mocker.patch("belay.cli.main.Device", return_value=mock_instance)
    return MockDevice(mock_class, mock_instance)


def test_sync_basic(mocker, mock_device):
    result = runner.invoke(app, ["sync", "/dev/ttyUSB0", "foo"])
    assert result.exit_code == 0
    mock_device.cls.assert_called_once_with("/dev/ttyUSB0", password="")
    mock_device.inst.sync.assert_called_once_with(
        PosixPath("foo"),
        dst="/",
        keep=[],
        ignore=[],
        mpy_cross_binary=None,
        progress_update=mocker.ANY,
    )
