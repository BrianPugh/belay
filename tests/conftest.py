from distutils import dir_util
from functools import partial
from pathlib import Path

import pytest
from typer.testing import CliRunner

import belay
from belay.cli import app


class MockDevice:
    def __init__(self, mocker):
        self.mocker = mocker
        self.inst = mocker.MagicMock()
        self.cls = None

    def patch(self, target: str):
        self.cls = self.mocker.patch(target, return_value=self.inst)

    def cls_assert_common(self):
        self.cls.assert_called_once_with("/dev/ttyUSB0", password="password")


@pytest.fixture
def mock_device(mocker):
    return MockDevice(mocker)


@pytest.fixture
def cli_runner(mock_device):
    cli_runner = CliRunner()

    def run(cmd, *args):
        result = cli_runner.invoke(
            app, [cmd, "/dev/ttyUSB0", *args, "--password", "password"]
        )
        mock_device.cls_assert_common()
        return result

    return run


@pytest.fixture
def emulated_device():
    device = belay.Device("exec:npm run --prefix rp2040js start:micropython")
    yield device
    device.close()


@pytest.fixture
def data_path(tmp_path, request):
    """Temporary copy of folder with same name as test module.

    Fixture responsible for searching a folder with the same name of test
    module and, if available, copying all contents to a temporary directory so
    tests can use them freely.
    """
    filename = Path(request.module.__file__)
    test_dir = filename.parent / filename.stem
    if test_dir.is_dir():
        dir_util.copy_tree(str(test_dir), str(tmp_path))

    return tmp_path
