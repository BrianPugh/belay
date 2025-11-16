from contextlib import contextmanager
from typing import Annotated

from cyclopts import Parameter

from belay.pyboard import PyboardException

# Custom annotated types for consistent CLI parameter help
PortStr = Annotated[
    str,
    Parameter(help="Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."),
]
PasswordStr = Annotated[
    str,
    Parameter(help="Password for communication methods (like WebREPL) that require authentication."),
]


@contextmanager
def remove_stacktrace():
    """Context manager that suppresses PyboardException stack traces and prints only the error message."""
    try:
        yield
    except PyboardException as e:
        print(e)
        # Exception is handled, don't re-raise
