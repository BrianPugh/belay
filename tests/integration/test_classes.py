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

        assert 10 == device.get_times_foo(1)
        assert 20 == device.get_times_foo(2)

        assert 42 == device.get_times_bar(1)
        assert 84 == device.get_times_bar(2)


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
