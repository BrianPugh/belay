import pytest

import belay
import belay.device


@pytest.fixture
def mock_pyboard(mocker):
    def mock_init(self, *args, **kwargs):
        self.serial = None

    exec_side_effect = [b'_BELAYR("micropython", (1, 19, 1), "rp2")\r\n'] * 100

    mocker.patch.object(belay.device.Pyboard, "__init__", mock_init)
    mocker.patch("belay.device.Pyboard.enter_raw_repl", return_value=None)
    mocker.patch("belay.device.Pyboard.exec", side_effect=exec_side_effect)
    mocker.patch("belay.device.Pyboard.fs_put")


@pytest.fixture
def mock_device(mock_pyboard):
    device = belay.Device()
    return device


def test_device_init(mock_device):
    """Just checks if everything in ``__init__`` is called fine."""


def test_device_init_no_startup(mock_pyboard):
    belay.Device(startup="")


def test_device_task(mocker, mock_device):
    mock_device._traceback_execute = mocker.MagicMock()

    @mock_device.task
    def foo(a, b):
        c = a + b  # noqa: F841

    mock_device._board.exec.assert_any_call("@__belay('foo')\ndef foo(a,b):\n c=a+b\n")

    foo(1, 2)
    assert (
        mock_device._traceback_execute.call_args.args[-1] == "_belay_foo(*(1, 2), **{})"
    )

    foo(1, b=2)
    assert (
        mock_device._traceback_execute.call_args.args[-1]
        == "_belay_foo(*(1,), **{'b': 2})"
    )


def test_device_task_chain(mocker, mock_pyboard):
    mock_device1 = belay.Device()
    mock_device1._traceback_execute = mocker.MagicMock(return_value=1)
    mock_device2 = belay.Device()
    mock_device2._traceback_execute = mocker.MagicMock(return_value=2)
    mock_device3 = belay.Device()
    mock_device3._traceback_execute = mocker.MagicMock(return_value=3)

    @mock_device1.task
    @mock_device2.task
    @mock_device3.task
    def foo(a, b):
        c = a + b  # noqa: F841

    res = foo("a", "b")

    assert res == [3, 2, 1]


def test_device_thread(mocker, mock_device):
    mock_device._traceback_execute = mocker.MagicMock()

    @mock_device.thread
    def foo(a, b):
        c = a + b  # noqa: F841

    mock_device._board.exec.assert_any_call("def foo(a,b):\n c=a+b\n")

    foo(1, 2)
    assert (
        mock_device._traceback_execute.call_args.args[-1]
        == "import _thread; _thread.start_new_thread(foo, (1, 2), {})"
    )

    foo(1, b=2)
    assert (
        mock_device._traceback_execute.call_args.args[-1]
        == "import _thread; _thread.start_new_thread(foo, (1,), {'b': 2})"
    )


def test_device_traceback_execute(mocker, mock_device, tmp_path):
    src_file = tmp_path / "main.py"
    src_file.write_text(
        "\n"
        "@device.task\n"
        "def f():\n"
        '    raise Exception("This is raised on-device.")'
    )
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
    cmd = None  # Doesn't matter; mocked
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
        belay.device._parse_belay_response("_BELAYA")


def test_parse_belay_response_stop_iteration():
    with pytest.raises(StopIteration):
        belay.device._parse_belay_response("_BELAYS")


def test_parse_belay_response_r():
    assert [1, 2, 3] == belay.device._parse_belay_response("_BELAYR[1,2,3]")
    assert 1 == belay.device._parse_belay_response("_BELAYR1")
    assert 1.23 == belay.device._parse_belay_response("_BELAYR1.23")
    assert "a" == belay.device._parse_belay_response("_BELAYR'a'")
    assert {1} == belay.device._parse_belay_response("_BELAYR{1}")
    assert b"foo" == belay.device._parse_belay_response("_BELAYRb'foo'")
    assert belay.device._parse_belay_response("_BELAYRFalse") is False
