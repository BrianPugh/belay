from inspect import isfunction

import pytest

from belay import Device, PyboardException


def test_classes_basic(emulate_command):
    class MyDevice(Device, skip=True):
        @Device.setup
        def setup():
            foo = 10  # noqa: F841
            bar = 42  # noqa: F841

        @Device.task
        def get_times_foo(val):
            return val * foo  # noqa: F821

        @Device.task
        def get_times_bar(val):
            return val * bar  # noqa: F821

    with MyDevice(emulate_command) as device:
        with pytest.raises(PyboardException):
            device("foo")  # it shouldn't exist yet

        device.setup()

        assert device.get_times_foo(1) == 10
        assert device.get_times_foo(2) == 20

        assert device.get_times_bar(1) == 42
        assert device.get_times_bar(2) == 84


def test_classes_setup_arguments(emulate_command):
    class MyDevice(Device, skip=True):
        @Device.setup
        def setup1(baz=1):
            foo = 11  # noqa: F841
            bar = 41  # noqa: F841

        @Device.setup()
        def setup2(baz=2):
            foo = 12  # noqa: F841
            bar = 42  # noqa: F841

    with MyDevice(emulate_command) as device:
        device.setup1(baz=111)
        assert device("foo") == 11
        assert device("bar") == 41
        assert device("baz") == 111

        device.setup2(baz=222)
        assert device("foo") == 12
        assert device("bar") == 42
        assert device("baz") == 222


def test_classes_setup_autoinit(emulate_command):
    class MyDevice(Device, skip=True):
        @Device.setup(autoinit=True)
        def setup1():
            foo = 10  # noqa: F841
            bar = 42  # noqa: F841

        @Device.setup(autoinit=True)
        def setup2():
            foo = 100  # noqa: F841

    with MyDevice(emulate_command) as device:
        # These 2 checks confirm ``setup2`` ran after ``setup1``.
        assert device("foo") == 100
        assert device("bar") == 42


def test_classes_setup_autoinit_arguments(emulate_command):
    with pytest.raises(ValueError):

        class MyDevice1(Device, skip=True):
            @Device.setup(autoinit=True)
            def setup(foo):
                pass

    with pytest.raises(ValueError):

        class MyDevice2(Device, skip=True):
            @Device.setup(autoinit=True)
            def setup(foo=1):
                pass

    with pytest.raises(ValueError):

        class MyDevice3(Device, skip=True):
            @Device.setup(autoinit=True)
            def setup(*, foo=1):
                pass


def test_classes_teardown(emulate_command):
    """Simply tests as its called and no uncaught exceptions occur."""

    class MyDevice(Device, skip=True):
        @Device.teardown
        def teardown():
            pass

    with MyDevice(emulate_command) as device:
        device.teardown()  # Testing that it can be directly called


def test_classes_teardown_mocked(emulate_command, mocker):
    """Tests if the teardown functions are executed on close."""

    class MyDevice(Device, skip=True):
        @Device.teardown
        def teardown():
            pass

    device = MyDevice(emulate_command)
    mock_teardown = mocker.MagicMock()
    device._belay_teardown._belay_executers[0] = mock_teardown
    device.close()
    mock_teardown.assert_called_once()


def test_classes_teardown_context_manager_mocked(emulate_command, mocker):
    """Tests if the teardown functions are executed on close."""

    class MyDevice(Device, skip=True):
        @Device.teardown
        def teardown():
            pass

    with MyDevice(emulate_command) as device:
        assert isfunction(device.teardown)
        assert device.teardown != device._belay_teardown
        assert len(device._belay_teardown._belay_executers) == 1

        mock_teardown = mocker.MagicMock()
        device._belay_teardown._belay_executers[0] = mock_teardown

    mock_teardown.assert_called_once()
