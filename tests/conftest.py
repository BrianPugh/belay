import os
from distutils import dir_util
from functools import partial
from pathlib import Path

import pytest
from typer.testing import CliRunner

import belay
import belay.cli.common
import belay.project
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


@pytest.fixture(autouse=True)
def cache_clear():
    belay.project.find_pyproject.cache_clear()
    belay.project.find_project_folder.cache_clear()
    belay.project.find_belay_folder.cache_clear()
    belay.project.find_dependencies_folder.cache_clear()
    belay.project.load_pyproject.cache_clear()
    belay.project.load_toml.cache_clear()
    belay.project.load_groups.cache_clear()


@pytest.fixture(autouse=True)
def restore_cwd():
    cwd = os.getcwd()  # noqa: PL109
    yield
    os.chdir(cwd)


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


@pytest.fixture(params=["micropython-v1.17.uf2", "circuitpython-v7.3.3.uf2"])
def emulate_command(request):
    return (
        f"exec:npm run --prefix rp2040js start:micropython -- --image={request.param}"
    )


@pytest.fixture
def emulated_device(emulate_command):
    with belay.Device(emulate_command) as device:
        yield device


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
