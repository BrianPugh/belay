import pytest

import belay


def test_task_exception(emulated_device, mocker):
    @emulated_device.task
    def foo(val):
        bar = 5
        baz  # Should cause an exception here!
        return 2 * val

    with pytest.raises(belay.PyboardException) as e:
        foo(10)

    expected_message = f'Traceback (most recent call last):\r\n  File "<stdin>", line 1, in <module>\r\n  File "{__file__}", line 10, in foo\n    baz  # Should cause an exception here!\nNameError: name \'baz\' isn\'t defined\r\n'
    assert e.value.args[0] == expected_message
