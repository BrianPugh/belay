def test_run_basic(mocker, mock_device, cli_runner, tmp_path):
    mock_device.patch("belay.cli.run.Device")
    py_file = tmp_path / "foo.py"
    py_file.write_text("print('hello')\nprint('world')")
    result = cli_runner("run", str(py_file))
    assert result.exit_code == 0
    mock_device.inst.assert_called_once_with("print('hello')\nprint('world')")
