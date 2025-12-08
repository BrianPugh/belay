import shutil
from contextlib import suppress
from pathlib import Path

import pytest

import belay
import belay.cli.common
import belay.project


def run_cli(app, args):
    """Run a CLI app with support for both Cyclopts v3 and v4.

    Cyclopts v3 returns None on success.
    Cyclopts v4 raises SystemExit with code 0 on success.

    Parameters
    ----------
    app : callable
        The CLI app to run.
    args : list
        Command line arguments.

    Returns
    -------
    int
        Exit code (0 for success).
    """
    try:
        result = app(args)
        # v3 behavior: returns None or int
        return result if isinstance(result, int) else 0
    except SystemExit as e:
        # v4 behavior: raises SystemExit
        return e.code if e.code is not None else 0


class MockDevice:
    def __init__(self, mocker):
        self.mocker = mocker
        self.inst = mocker.MagicMock()
        self.inst.__enter__.return_value = self.inst  # Support context manager use.
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
    belay.project.find_cache_folder.cache_clear()
    belay.project.find_cache_dependencies_folder.cache_clear()
    belay.project.load_pyproject.cache_clear()
    belay.project.load_toml.cache_clear()
    belay.project.load_groups.cache_clear()


@pytest.fixture
def tmp_cwd(tmp_path, monkeypatch):
    """Change to a temporary directory for the duration of the test."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def mock_device(mocker):
    return MockDevice(mocker)


ALL_FIRMWARES = [
    "micropython-v1.17.uf2",
    "micropython-v1.24.1.uf2",
    "circuitpython-v7.3.3.uf2",
    "circuitpython-v8.0.0.uf2",
    "circuitpython-v9.2.0.uf2",
]
SHORT_FIRMWARES = [
    "micropython-v1.17.uf2",
]


@pytest.fixture
def emulate_command(request):
    firmware = request.param
    firmware_file = Path("rp2040js") / firmware
    if not firmware_file.exists():
        pytest.fail(
            f"Firmware file not found: {firmware_file}. Run 'make download-firmware' to download required files."
        )
    return f"exec:npm run --prefix rp2040js start:micropython -- --image={firmware}"


def pytest_generate_tests(metafunc):
    if "emulate_command" in metafunc.fixturenames:
        if metafunc.config.getoption("--long-integration"):
            firmwares = ALL_FIRMWARES
        else:
            firmwares = SHORT_FIRMWARES
        metafunc.parametrize("emulate_command", firmwares, indirect=True)


@pytest.fixture
def emulated_device(emulate_command):
    device = None
    try:
        device = belay.Device(emulate_command)
        yield device
    finally:
        if device is not None:
            with suppress(Exception):
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
        shutil.copytree(test_dir, tmp_path, dirs_exist_ok=True)

    return tmp_path


def pytest_addoption(parser):
    parser.addoption(
        "--network",
        action="store_true",
        help="Include tests that interact with network (marked with marker @network)",
    )
    parser.addoption(
        "--long-integration",
        action="store_true",
        help="Run integration tests with all firmwares instead of just micropython-v1.17.",
    )


def pytest_runtest_setup(item):
    if "network" in item.keywords and not item.config.getoption("--network"):
        pytest.skip("need --network option to run this test")
