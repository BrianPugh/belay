from belay.pyboard import PyboardException

help_port = "Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."
help_password = "Password for communication methods (like WebREPL) that require authentication."  # nosec  # noqa: S105


class remove_stacktrace:  # noqa: N801
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and issubclass(exc_type, PyboardException):
            print(exc_value)
            return True  # suppress the full stack trace
        else:
            return False  # let other exceptions propagate normally
