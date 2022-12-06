import pytest

import belay


def test_call_various(emulated_device):
    assert emulated_device("foo = 25") is None
    assert emulated_device("foo") == 25

    with pytest.raises(belay.PyboardException):
        emulated_device("bar")
