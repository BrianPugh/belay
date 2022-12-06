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
