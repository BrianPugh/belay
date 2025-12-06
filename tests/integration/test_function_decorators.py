import pytest

import belay
from belay import Device


def test_setup_basic(emulated_device):
    @emulated_device.setup
    def setup(config):
        foo = config["bar"]  # noqa: F841

    setup({"bar": 25})

    assert emulated_device("config") == {"bar": 25}
    assert emulated_device("foo") == 25


def test_task_basic(emulated_device, mocker):
    spy_parse_belay_response = mocker.spy(belay.device, "parse_belay_response")

    @emulated_device.task
    def foo(val):
        return 2 * val

    @emulated_device.task
    def bytes_task():
        return b"\x00\x01\x02"

    assert foo(5) == 10

    # Response format is _BELAYR|{time}|{value}
    call_args = spy_parse_belay_response.call_args[0][0]
    assert call_args.startswith("_BELAYR|")
    assert "|10\r\n" in call_args

    assert bytes_task() == b"\x00\x01\x02"


def test_task_basic_trusted(emulated_device, mocker):
    @emulated_device.task(trusted=True)
    def foo():
        return bytearray(b"\x01")

    res = foo()
    assert isinstance(res, bytearray)
    assert res == bytearray(b"\x01")


def test_task_generators_basic(emulated_device, mocker):
    spy_parse_belay_response = mocker.spy(belay.device, "parse_belay_response")

    @emulated_device.task
    def my_gen(val):
        i = 0
        while True:
            yield i
            i += 1
            if i == val:
                break

    actual = list(my_gen(3))
    assert actual == [0, 1, 2]
    # Check that we got calls with the expected values (timestamp format will vary)
    calls = [str(call) for call in spy_parse_belay_response.call_args_list]
    assert any("|0\\r\\n" in call for call in calls)
    assert any("|1\\r\\n" in call for call in calls)
    assert any("|2\\r\\n" in call for call in calls)


def test_task_generators_communicate(emulated_device):
    @emulated_device.task
    def my_gen(x):
        x = yield x
        x = yield x

    generator = my_gen(5)
    actual = []
    actual.append(generator.send(None))
    actual.append(generator.send(25))
    with pytest.raises(StopIteration):
        generator.send(50)
    assert actual == [5, 25]


def test_teardown(emulated_device, mocker):
    @emulated_device.teardown
    def foo():
        pass

    mock_teardown = mocker.MagicMock()
    assert len(emulated_device._belay_teardown._belay_executers) == 1
    emulated_device._belay_teardown._belay_executers[0] = mock_teardown

    emulated_device.close()

    mock_teardown.assert_called_once()


def test_classdecorator_setup():
    @Device.setup
    def foo1():
        pass

    @Device.setup()
    def foo2():
        pass

    @Device.setup(autoinit=True)
    def foo3():
        pass

    with pytest.raises(ValueError):
        # Provided an arg with autoinit=True is not allowed.

        @Device.setup(autoinit=True)
        def foo(arg1=1):
            pass
