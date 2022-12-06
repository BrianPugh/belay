import pytest

import belay


def test_generators_basic(emulated_device):
    @emulated_device.task
    def my_gen(val):
        i = 0
        while True:
            yield i
            i += 1
            if i == val:
                break

    assert [0, 1, 2] == list(my_gen(3))


def test_generators_communicate(emulated_device):
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
