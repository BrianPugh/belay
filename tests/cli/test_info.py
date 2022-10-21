def test_info_basic(mocker, mock_device, cli_runner, tmp_path):
    mock_device.patch("belay.cli.main.Device")
    mock_device.inst.implementation.name = "testingpython"
    mock_device.inst.implementation.version = (4, 7, 9)
    mock_device.inst.implementation.platform = "pytest"
    result = cli_runner("info")
    assert result.exit_code == 0
    assert result.output == "testingpython v4.7.9 - pytest\n"
