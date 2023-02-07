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
