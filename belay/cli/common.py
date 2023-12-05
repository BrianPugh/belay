from belay.pyboard import PyboardException


class remove_stacktrace:  # noqa: N801
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and issubclass(exc_type, PyboardException):
            print(exc_value)
            return True  # suppress the full stack trace
        else:
            return False  # let other exceptions propagate normally
