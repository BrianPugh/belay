import math
from dataclasses import dataclass
from threading import Lock
from typing import Callable, Literal, Optional, get_args

from attrs import define, field

Architectures = Literal[
    None,
    "x86",
    "x64",
    "armv6",
    "armv6m",
    "armv7m",
    "armv7em",
    "armv7emsp",
    "armv7emdp",
    "xtensa",
    "xtensawin",
    "rv32imc",
]


def _arch_converter(x: Optional[int]) -> Optional[Architectures]:
    if x is None:
        return None
    arch = get_args(Architectures)[x >> 10]
    return arch


@define
class Implementation:
    """Implementation dataclass detailing the device.

    Parameters
    ----------
    name: str
        Type of python running on device.
        One of ``{"micropython", "circuitpython"}``.
    version: Tuple[int, int, int]
        ``(major, minor, patch)`` Semantic versioning of device's firmware.
    platform: str
        Board identifier. May not be consistent from MicroPython to CircuitPython.
        e.g. The Pi Pico is "rp2" in MicroPython, but "RP2040"  in CircuitPython.
    emitters: tuple[str]
        Tuple of available emitters on-device ``{"native", "viper"}``.
    """

    name: str
    version: tuple[int, int, int] = (0, 0, 0)
    platform: str = ""
    arch: Optional[str] = field(default=None, converter=_arch_converter)
    emitters: tuple[str, ...] = ()


_method_metadata_counter_lock = Lock()
_method_metadata_counter = 0


@dataclass
class MethodMetadata:
    """Metadata for executer-decorated Device methods."""

    executer: Callable
    kwargs: dict
    autoinit: bool = False  # Only applies to ``SetupExecuter``.
    implementation: Optional[str] = None

    id: int = -1  # monotonically increasing global identifier.

    def __post_init__(self):
        global _method_metadata_counter
        with _method_metadata_counter_lock:
            self.id = _method_metadata_counter
            _method_metadata_counter += 1


def sort_executers(executers):
    """Sorts executers by monotonically increasing ``__belay__.id``.

    This ensures that, when necessary, executers are called in the order they are defined.
    """

    def get_key(x):
        try:
            return x.__wrapped__.__belay__.id
        except AttributeError:
            return math.inf

    return sorted(executers, key=get_key)
