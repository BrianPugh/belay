import pytest

import belay
import belay.device
from belay import Device
from belay.exceptions import NoMatchingExecuterError


@pytest.fixture
def mock_pyboard(mocker):
    device_time = [42.5]  # Starting device time

    def mock_init(self, *args, **kwargs):
        self.serial = mocker.MagicMock()

    def mock_exec(cmd, data_consumer=None):
        # Handle different command types
        if "__belay_timed_repr(__belay_monotonic())" in cmd:
            # Time query with dual timestamps using new helper
            t1 = device_time[0]
            device_time[0] += 0.0005  # Small increment for execution time
            t2 = device_time[0]
            device_time[0] += 0.0005
            avg_time = (t1 + t2) / 2
            data = f"_BELAYR|{avg_time}|{t2}\r\n".encode()
        elif "implementation" in cmd and "name" in cmd:
            # Implementation detection (without timing)
            data = b'_BELAYR||("micropython", (1, 19, 1), "rp2")\r\n'
        elif "def __belay" in cmd:
            # Loading snippets
            data = b""
        else:
            # Default empty response
            data = b""

        if data_consumer and data:
            data_consumer(data)

    mocker.patch.object(belay.device.Pyboard, "__init__", mock_init)
    mocker.patch.object(belay.device.Pyboard, "exec", side_effect=mock_exec)
    mocker.patch("belay.device.Pyboard.enter_raw_repl", return_value=None)
    mocker.patch("belay.device.Pyboard.fs_put")


@pytest.fixture
def mock_device(mock_pyboard):
    with belay.Device(auto_sync_time=False) as device:
        yield device


def test_device_init(mock_device):
    """Just checks if everything in ``__init__`` is called fine."""


def test_device_init_no_startup(mock_pyboard):
    belay.Device(startup="", auto_sync_time=False)


def test_device_task(mocker, mock_device):
    mock_device._traceback_execute = mocker.MagicMock()

    @mock_device.task
    def foo(a, b):
        c = a + b  # noqa: F841

    mock_device._board.exec.assert_any_call("def foo(a,b):\n c=a+b\n", data_consumer=mocker.ANY)

    foo(1, 2)
    assert mock_device._traceback_execute.call_args.args[-1] == "foo(*(1, 2), **{})"

    foo(1, b=2)
    assert mock_device._traceback_execute.call_args.args[-1] == "foo(*(1,), **{'b': 2})"


def test_device_thread(mocker, mock_device):
    mock_device._traceback_execute = mocker.MagicMock()

    @mock_device.thread
    def foo(a, b):
        c = a + b  # noqa: F841

    mock_device._board.exec.assert_any_call("def foo(a,b):\n c=a+b\n", data_consumer=mocker.ANY)

    foo(1, 2)
    assert (
        mock_device._traceback_execute.call_args.args[-1] == "import _thread; _thread.start_new_thread(foo, (1, 2), {})"
    )

    foo(1, b=2)
    assert (
        mock_device._traceback_execute.call_args.args[-1]
        == "import _thread; _thread.start_new_thread(foo, (1,), {'b': 2})"
    )


def test_device_traceback_execute(mocker, mock_device, tmp_path):
    src_file = tmp_path / "main.py"
    src_file.write_text('\n@device.task\ndef f():\n    raise Exception("This is raised on-device.")')
    exception = belay.PyboardException(
        "Traceback (most recent call last):\r\n"
        '  File "<stdin>", line 1, in <module>\r\n'
        '  File "<stdin>", line 4, in belay_interface\r\n'
        '  File "<stdin>", line 3, in foo\r\n'
        "Exception: This is raised on-device.\r\n"
    )
    mock_device._board.exec = mocker.MagicMock(side_effect=exception)

    src_lineno = 2
    name = "foo"
    cmd = ""  # Doesn't matter; mocked
    expected_msg = (
        "Traceback (most recent call last):\r\n"
        '  File "<stdin>", line 1, in <module>\r\n'
        '  File "<stdin>", line 4, in belay_interface\r\n'
        f'  File "{src_file}", line 4, in foo\n'
        '    raise Exception("This is raised on-device.")\n'
        "Exception: This is raised on-device.\r\n"
    )
    with pytest.raises(belay.PyboardException) as exc_info:
        mock_device._traceback_execute(src_file, src_lineno, name, cmd)
    assert exc_info.value.args[0] == expected_msg


def test_parse_belay_response_unknown():
    with pytest.raises(ValueError):
        belay.device.parse_belay_response("_BELAYA")


def test_parse_belay_response_stop_iteration():
    with pytest.raises(StopIteration):
        belay.device.parse_belay_response("_BELAYS")


def test_parse_belay_response_r():
    # _BELAYR{id}|{time}|{value}
    assert belay.device.parse_belay_response("_BELAYR||[1,2,3]") == (belay.device.NO_RESULT, [1, 2, 3], None)
    assert belay.device.parse_belay_response("_BELAYR||1") == (belay.device.NO_RESULT, 1, None)
    assert belay.device.parse_belay_response("_BELAYR||1.23") == (belay.device.NO_RESULT, 1.23, None)
    assert belay.device.parse_belay_response("_BELAYR||'a'") == (belay.device.NO_RESULT, "a", None)
    assert belay.device.parse_belay_response("_BELAYR||{1}") == (belay.device.NO_RESULT, {1}, None)
    assert belay.device.parse_belay_response("_BELAYR||b'foo'") == (belay.device.NO_RESULT, b"foo", None)
    assert belay.device.parse_belay_response("_BELAYR||False") == (belay.device.NO_RESULT, False, None)
    # With timestamp (in milliseconds, converted to seconds)
    assert belay.device.parse_belay_response("_BELAYR|42500|123") == (belay.device.NO_RESULT, 123, 42.5)


def test_overload_executer_mixing_error():
    with pytest.raises(ValueError):

        class MyDevice1(Device, skip=True):
            def foo():
                pass

            @Device.task(implementation="circuitpython")
            def foo():  # noqa: F811
                pass

    with pytest.raises(ValueError):

        class MyDevice2(Device, skip=True):
            @Device.task(implementation="circuitpython")
            def foo():
                pass

            def foo():  # noqa: F811
                pass


def test_overload_executer_after_catchall_error():
    with pytest.raises(ValueError):

        class MyDevice(Device, skip=True):
            @Device.task
            def foo():
                pass

            @Device.task(implementation="circuitpython")
            def foo():  # noqa: F811
                pass


def test_overload_executer_no_matching_error(mock_pyboard):
    class MyDevice(Device):
        @Device.task(implementation="missing_implementation")
        def foo():
            pass

    with pytest.raises(NoMatchingExecuterError):
        MyDevice()
