# Don't manually change, let poetry-dynamic-versioning-plugin handle it.
__version__ = "0.0.0"

__all__ = [
    "AuthenticationError",
    "ConnectionLost",
    "Device",
    "FeatureUnavailableError",
    "Implementation",
    "MaxHistoryLengthError",
    "PyboardException",
    "SpecialFunctionNameError",
    "list_devices",
    "minify",
    "setup",
    "task",
    "teardown",
    "thread",
]
from ._minify import minify
from .device import Device, Implementation
from .exceptions import (
    AuthenticationError,
    ConnectionLost,
    FeatureUnavailableError,
    MaxHistoryLengthError,
    SpecialFunctionNameError,
)
from .helpers import list_devices
from .pyboard import PyboardException

setup = Device.setup
task = Device.task
thread = Device.thread
teardown = Device.teardown
