from posixpath import join
from unittest.mock import call

import pytest

import belay


@pytest.fixture
def mock_pyboard(mocker):
    mocker.patch("belay.device.Pyboard.__init__", return_value=None)
    mocker.patch("belay.device.Pyboard.enter_raw_repl", return_value=None)
    mocker.patch("belay.device.Pyboard.exec", return_value=b"null")
    mocker.patch("belay.device.Pyboard.fs_put")


@pytest.fixture
def mock_device(mock_pyboard):
    device = belay.Device()
    return device


def test_device_init(mock_device):
    pass


def test_device_init_no_startup(mock_pyboard):
    belay.Device(startup="")


def test_device_task(mocker, mock_device):
    mock_device._traceback_execute = mocker.MagicMock()

    @mock_device.task
    def foo(a, b):
        c = a + b  # noqa: F841

    mock_device._board.exec.assert_any_call("@json_decorator\ndef foo(a,b):\n c=a+b\n")

    foo(1, 2)
    assert (
        mock_device._traceback_execute.call_args.args[-1]
        == "__belay_foo(*(1, 2), **{})"
    )

    foo(1, b=2)
    assert (
        mock_device._traceback_execute.call_args.args[-1]
        == "__belay_foo(*(1,), **{'b': 2})"
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


@pytest.fixture
def sync_path(tmp_path):
    (tmp_path / "alpha.py").write_text("def alpha():\n    pass")
    (tmp_path / "bar.txt").write_text("bar contents")
    (tmp_path / "foo.txt").write_text("foo contents")
    (tmp_path / "folder1" / "folder1_1").mkdir(parents=True)
    (tmp_path / "folder1" / "file1.txt").write_text("file1 contents")
    (tmp_path / "folder1" / "folder1_1" / "file1_1.txt").write_text("file1_1 contents")

    return tmp_path


def test_device_sync_empty_remote(mocker, mock_device, sync_path):
    mock_device._traceback_execute = mocker.MagicMock(return_value="0" * 64)

    mock_device.sync(sync_path)

    expected_cmds = [
        "__belay_remote_hash_file(*('/alpha.py',), **{})",
        "__belay_remote_hash_file(*('/bar.txt',), **{})",
        "__belay_remote_hash_file(*('/folder1/file1.txt',), **{})",
        "__belay_remote_hash_file(*('/folder1/folder1_1/file1_1.txt',), **{})",
        "__belay_remote_hash_file(*('/foo.txt',), **{})",
    ]
    call_args_list = mock_device._traceback_execute.call_args_list
    assert len(expected_cmds) == len(call_args_list)
    for actual_call, expected_cmd in zip(call_args_list, expected_cmds):
        assert actual_call.args[-1] == expected_cmd

    mock_device._board.fs_put.assert_has_calls(
        [
            call(sync_path / "bar.txt", "/bar.txt"),
            call(sync_path / "folder1/file1.txt", "/folder1/file1.txt"),
            call(
                sync_path / "folder1/folder1_1/file1_1.txt",
                "/folder1/folder1_1/file1_1.txt",
            ),
            call(sync_path / "foo.txt", "/foo.txt"),
        ]
    )


def test_device_sync_partial_remote(mocker, mock_device, sync_path):
    def __belay_remote_hash_file(fn):
        local_fn = sync_path / fn[1:]
        if local_fn.stem.endswith("1"):
            return "0" * 64
        else:
            return belay.device.local_hash_file(local_fn)

    def side_effect(src_file, src_lineno, name, cmd):
        nonlocal __belay_remote_hash_file
        return eval(cmd)

    mock_device._traceback_execute = mocker.MagicMock(side_effect=side_effect)

    mock_device.sync(sync_path)

    mock_device._board.fs_put.assert_has_calls(
        [
            call(sync_path / "folder1/file1.txt", "/folder1/file1.txt"),
            call(
                sync_path / "folder1/folder1_1/file1_1.txt",
                "/folder1/folder1_1/file1_1.txt",
            ),
        ]
    )
