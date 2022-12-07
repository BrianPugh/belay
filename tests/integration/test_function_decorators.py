import pytest

import belay


def test_setup_basic(emulated_device):
    @emulated_device.setup
    def setup(config):
        foo = config["bar"]  # noqa: F841

    setup({"bar": 25})

    assert {"bar": 25} == emulated_device("config")
    assert 25 == emulated_device("foo")


def test_task_basic(emulated_device, mocker):
    spy_parse_belay_response = mocker.spy(belay.device, "_parse_belay_response")

    @emulated_device.task
    def foo(val):
        return 2 * val

    assert 10 == foo(5)

    spy_parse_belay_response.assert_called_once_with("_BELAYR10\r\n")


def test_task_generators_basic(emulated_device, mocker):
    spy_parse_belay_response = mocker.spy(belay.device, "_parse_belay_response")

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
    spy_parse_belay_response.assert_has_calls(
        [
            mocker.call("_BELAYR0\r\n"),
            mocker.call("_BELAYR1\r\n"),
            mocker.call("_BELAYR2\r\n"),
            mocker.call("_BELAYS\r\n"),
        ]
    )


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
    assert [5, 25] == actual
