# Don't manually change, let poetry-dynamic-versioning-plugin handle it.
__version__ = "0.0.0"

__all__ = [
    "AuthenticationError",
    "ConnectionFailedError",
    "ConnectionLost",
    "Device",
    "DeviceNotFoundError",
    "FeatureUnavailableError",
    "Implementation",
    "InsufficientSpecifierError",
    "MaxHistoryLengthError",
    "NoMatchingExecuterError",
    "NotBelayResponseError",
    "PyboardException",
    "SpecialFunctionNameError",
    "UsbSpecifier",
    "list_devices",
    "minify",
]
from ._minify import minify
from .device import Device, Implementation
from .exceptions import (
    AuthenticationError,
    ConnectionFailedError,
    ConnectionLost,
    DeviceNotFoundError,
    FeatureUnavailableError,
    InsufficientSpecifierError,
    MaxHistoryLengthError,
    NoMatchingExecuterError,
    NotBelayResponseError,
    SpecialFunctionNameError,
)
from .helpers import list_devices
from .pyboard import PyboardException
from .usb_specifier import UsbSpecifier
