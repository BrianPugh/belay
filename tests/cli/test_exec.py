def test_exec_basic(mocker, mock_device, cli_runner):
    mock_device.patch("belay.cli.main.Device")
    result = cli_runner("exec", "print('hello world')")
    assert result.exit_code == 0
    mock_device.inst.assert_called_once_with("print('hello world')")
