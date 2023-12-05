def test_info_basic(mock_device, cli_runner, capsys):
    mock_device.patch("belay.cli._info.Device")
    mock_device.inst.implementation.name = "testingpython"
    mock_device.inst.implementation.version = (4, 7, 9)
    mock_device.inst.implementation.platform = "pytest"
    assert not cli_runner("info")
    captured = capsys.readouterr()
    assert captured.out == "testingpython v4.7.9 - pytest\n"
