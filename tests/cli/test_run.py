def test_run_basic(mock_device, cli_runner, tmp_path):
    mock_device.patch("belay.cli._run.Device")
    py_file = tmp_path / "foo.py"
    py_file.write_text("print('hello')\nprint('world')")
    assert not cli_runner("run", str(py_file))
    mock_device.inst.assert_called_once_with("print('hello')\nprint('world')")
