import ast
from pathlib import PosixPath
from unittest.mock import call

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


@pytest.fixture
def sync_path(tmp_path):
    (tmp_path / "alpha.py").write_text("def alpha():\n    pass")
    (tmp_path / "bar.txt").write_text("bar contents")
    (tmp_path / "foo.txt").write_text("foo contents")
    (tmp_path / "folder1" / "folder1_1").mkdir(parents=True)
    (tmp_path / "folder1" / "file1.txt").write_text("file1 contents")
    (tmp_path / "folder1" / "folder1_1" / "file1_1.txt").write_text("file1_1 contents")

    return tmp_path


@pytest.fixture
def sync_begin():
    exec(belay.device._read_snippet("sync_begin"), globals())


def test_sync_device_belay_hf(sync_begin, tmp_path):
    """Test on-device FNV-1a hash implementation.

    Test vector from: http://www.isthe.com/chongo/src/fnv/test_fnv.c
    """
    f = tmp_path / "test_file"
    f.write_text("foobar")
    actual = __belay_hf(str(f))  # noqa: F821
    assert actual == 0x85944171F73967E8


def test_sync_device_belay_hfs(sync_begin, capsys, tmp_path):
    fooba_file = tmp_path / "fooba_file"
    fooba_file.write_text("fooba")

    foobar_file = tmp_path / "foobar_file"
    foobar_file.write_text("foobar")

    return_value = __belay_hfs([str(fooba_file), str(foobar_file)])  # noqa: F821
    assert return_value is None
    captured = capsys.readouterr()
    # Test Hashes:
    #     0xcac165afa2fef40a,  # fooba
    #     0x85944171f73967e8,  # foobar
    assert captured.out == "_BELAYR[14610070471194899466, 9625390261332436968]\n"


def test_sync_device_belay_mkdirs(sync_begin):
    pass


def test_sync_device_belay_fs(sync_begin):
    pass


def test_device_sync_empty_remote(mocker, mock_device, sync_path):
    payload = ("_BELAYR" + repr([b""] * 5) + "\r\n").encode("utf-8")
    mock_device._board.exec = mocker.MagicMock(return_value=payload)

    mock_device.sync(sync_path)

    mock_device._board.exec.assert_has_calls(
        [
            call(
                "for x in['/alpha.py','/bar.txt','/folder1/file1.txt','/folder1/folder1_1/file1_1.txt','/foo.txt','/boot.py','/webrepl_cfg.py']:\n all_files.discard(x)"
            ),
            call("__belay_mkdirs(['/folder1','/folder1/folder1_1'])"),
            call(
                "__belay_hfs(['/alpha.py','/bar.txt','/folder1/file1.txt','/folder1/folder1_1/file1_1.txt','/foo.txt'])"
            ),
        ]
    )

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
    def __belay_hfs(fns):
        out = []
        for fn in fns:
            local_fn = sync_path / fn[1:]
            if local_fn.stem.endswith("1"):
                out.append(b"\x00")
            else:
                out.append(belay.device._local_hash_file(local_fn))
        return out

    def side_effect(cmd):
        if not cmd.startswith("__belay_hfs"):
            return b""
        nonlocal __belay_hfs
        return ("_BELAYR" + repr(eval(cmd)) + "\r\n").encode("utf-8")

    mock_device._board.exec = mocker.MagicMock(side_effect=side_effect)

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


def test_discover_files_dirs_typical(tmp_path):
    (tmp_path / "file1.ext").touch()
    (tmp_path / "file2.ext").touch()
    (tmp_path / "folder1").mkdir()
    (tmp_path / "folder1" / "file3.ext").touch()

    remote_dir = "/foo/bar"
    src_files, src_dirs, dst_files = belay.device._discover_files_dirs(
        remote_dir=remote_dir,
        local_file_or_folder=tmp_path,
    )

    src_files = [x.relative_to(tmp_path) for x in src_files]
    src_dirs = [x.relative_to(tmp_path) for x in src_dirs]
    assert src_files == [
        PosixPath("file1.ext"),
        PosixPath("file2.ext"),
        PosixPath("folder1/file3.ext"),
    ]
    assert src_dirs == [PosixPath("folder1")]
    assert dst_files == [
        PosixPath("/foo/bar/file1.ext"),
        PosixPath("/foo/bar/file2.ext"),
        PosixPath("/foo/bar/folder1/file3.ext"),
    ]


def test_discover_files_dirs_empty(tmp_path):
    remote_dir = "/foo/bar"
    src_files, src_dirs, dst_files = belay.device._discover_files_dirs(
        remote_dir=remote_dir,
        local_file_or_folder=tmp_path,
    )

    assert src_files == []
    assert src_dirs == []
    assert dst_files == []


def test_discover_files_dirs_single_file(tmp_path):
    single_file = tmp_path / "file1.ext"
    single_file.touch()

    remote_dir = "/foo/bar"
    src_files, src_dirs, dst_files = belay.device._discover_files_dirs(
        remote_dir=remote_dir,
        local_file_or_folder=single_file,
    )

    src_files = [x.relative_to(tmp_path) for x in src_files]
    src_dirs = [x.relative_to(tmp_path) for x in src_dirs]
    assert src_files == [PosixPath("file1.ext")]
    assert src_dirs == []
    assert dst_files == [PosixPath("/foo/bar/file1.ext")]
