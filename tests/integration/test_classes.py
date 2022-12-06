import pytest

from belay import Device


def test_classes_basic(emulate_command):
    class MyDevice(Device):
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
        device.setup()

        assert 10 == device.get_times_foo(1)
        assert 20 == device.get_times_foo(2)

        assert 42 == device.get_times_bar(1)
        assert 84 == device.get_times_bar(2)
