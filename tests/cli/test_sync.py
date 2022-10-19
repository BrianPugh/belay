from pathlib import PosixPath


def test_sync_basic(mocker, mock_device, cli_runner):
    mock_device.patch("belay.cli.main.Device")
    result = cli_runner("sync", "foo")
    assert result.exit_code == 0
    mock_device.inst.sync.assert_called_once_with(
        PosixPath("foo"),
        dst="/",
        keep=[],
        ignore=[],
        mpy_cross_binary=None,
        progress_update=mocker.ANY,
    )
