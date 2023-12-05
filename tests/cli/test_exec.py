def test_exec_basic(mock_device, cli_runner):
    mock_device.patch("belay.cli._exec.Device")
    assert not cli_runner("exec", "print('hello world')")
    mock_device.inst.assert_called_once_with("print('hello world')")
