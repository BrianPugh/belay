import re

import belay


class StreamOut:
    def __init__(self):
        self.out = ""

    def write(self, data):
        self.out += data


def test_print_basic(emulated_device, mocker):
    spy_parse_belay_response = mocker.spy(belay.device, "parse_belay_response")

    @emulated_device.task
    def foo():
        print("print from belay task.")

    stream_out = StreamOut()
    res = emulated_device("foo()", stream_out=stream_out)

    # Verify the correct calls were made
    assert len(spy_parse_belay_response.call_args_list) == 2
    assert spy_parse_belay_response.call_args_list[0][0][0] == "print from belay task.\r\n"

    # Second call should match pattern: _BELAYR|{timestamp}|None\r\n
    second_call = spy_parse_belay_response.call_args_list[1][0][0]
    assert re.match(
        r"^_BELAYR\|\d+\|None\r\n$", second_call
    ), f"Expected pattern '_BELAYR|<timestamp>|None\\r\\n' but got: {second_call!r}"

    assert stream_out.out == "print from belay task.\r\n"
    assert res is None
