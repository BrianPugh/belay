import pytest

import belay
import belay.device
from belay import Device
from belay.exceptions import NoMatchingExecuterError


@pytest.fixture
def mock_pyboard(mocker):
    exec_side_effect = [b'_BELAYR("micropython", (1, 19, 1), "rp2")\r\n'] * 100

    def mock_init(self, *args, **kwargs):
        self.serial = mocker.MagicMock()

    def mock_exec(cmd, data_consumer=None):
        data = exec_side_effect.pop()
        if data_consumer:
            data_consumer(data)

    mocker.patch.object(belay.device.Pyboard, "__init__", mock_init)
    mocker.patch.object(belay.device.Pyboard, "exec", side_effect=mock_exec)
    mocker.patch("belay.device.Pyboard.enter_raw_repl", return_value=None)
    mocker.patch("belay.device.Pyboard.fs_put")


@pytest.fixture
def mock_device(mock_pyboard):
    with belay.Device() as device:
        yield device


def test_device_init(mock_device):
    """Just checks if everything in ``__init__`` is called fine."""


def test_device_init_no_startup(mock_pyboard):
    belay.Device(startup="")


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
    assert belay.device.parse_belay_response("_BELAYR[1,2,3]") == [1, 2, 3]
    assert belay.device.parse_belay_response("_BELAYR1") == 1
    assert belay.device.parse_belay_response("_BELAYR1.23") == 1.23
    assert belay.device.parse_belay_response("_BELAYR'a'") == "a"
    assert {1} == belay.device.parse_belay_response("_BELAYR{1}")
    assert belay.device.parse_belay_response("_BELAYRb'foo'") == b"foo"
    assert belay.device.parse_belay_response("_BELAYRFalse") is False


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
