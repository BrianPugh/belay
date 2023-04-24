# Don't manually change, let poetry-dynamic-versioning-plugin handle it.
__version__ = "0.0.0"

__all__ = [
    "AuthenticationError",
    "ConnectionFailedError",
    "ConnectionLost",
    "Device",
    "DeviceMeta",
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
from .device_meta import DeviceMeta
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
from .pyboard import PyboardException
from .usb_specifier import UsbSpecifier, list_devices
