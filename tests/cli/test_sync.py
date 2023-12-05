from pathlib import Path


def test_sync_basic(mocker, mock_device, cli_runner):
    mock_device.patch("belay.cli._sync.Device")
    assert not cli_runner("sync", "foo")
    mock_device.inst.sync.assert_called_once_with(
        Path("foo"),
        dst="/",
        keep=None,
        ignore=None,
        mpy_cross_binary=None,
        progress_update=mocker.ANY,
    )
