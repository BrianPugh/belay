import belay


class StreamOut:
    def __init__(self):
        self.out = ""

    def write(self, data):
        self.out += data


def test_print_basic(emulated_device, mocker):
    spy_parse_belay_response = mocker.spy(belay.device, "_parse_belay_response")

    @emulated_device.task
    def foo():
        print("print from belay task.")

    stream_out = StreamOut()
    res = emulated_device("foo()", stream_out=stream_out)

    spy_parse_belay_response.assert_has_calls(
        [
            mocker.call("print from belay task.\r\n"),
            mocker.call("_BELAYRNone\r\n"),
        ]
    )
    assert len(spy_parse_belay_response.call_args_list) == 2

    assert stream_out.out == "print from belay task.\r\n"
    assert res is None
