import itertools
import math
from typing import Callable, Literal, Optional, get_args

from attrs import define, field

from .exceptions import BelayException


class DeviceResetDetected(BelayException):
    """Device reset detected via time-based prediction during tick unwrapping."""


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


@define
class TimeSync:
    """Time synchronization state for handling tick-based timestamps with wrap-around.

    Manages the offset between device monotonic time and host time, and handles
    wrap-around of device tick counters.

    Parameters
    ----------
    ticks_max : int
        Maximum tick value before wrap-around (e.g., 2^30-1 for MicroPython)
    """

    ticks_max: Optional[int] = None
    """Implementation-specific max value. Typically something like ``(1 << 29) - 1``"""

    alpha: float = 0.1
    """Exponential moving average smoothing factor in range [0, 1].

    Smaller values result in the offset reacting slower and smoother.
    Larger values result in the offset reacting quicker and jerkier.
    """

    time_offset: Optional[float] = field(default=None, init=False)
    """Time offset between device and host in seconds (device_time - host_time).

    None until first synchronization is performed. Used to convert between
    device timestamps and host timestamps.
    """

    _reference_host_time: Optional[float] = field(default=None, init=False)
    """Host time (seconds) when the reference device tick was captured.

    Used as the baseline for time-based prediction of device tick progression.
    None until first tick is received.
    """

    _reference_device_tick_unwrapped: Optional[int] = field(default=None, init=False)
    """Unwrapped device tick value (milliseconds) at the reference host time.

    Establishes the baseline for all future unwrapped tick calculations. This is
    the unwrapped value assigned to the first reading, ensuring monotonicity of
    all subsequent unwrapped values. None until first tick is received.
    """

    @property
    def _ticks_period(self) -> int:
        if self.ticks_max is None:
            raise ValueError("ticks_max not initialized - TimeSync must be configured before use")
        return self.ticks_max + 1

    def unwrap_tick(self, raw_tick: int, current_host_time: float) -> int:
        """Unwrap a raw tick value using time-based prediction.

        Uses elapsed host time to predict expected device time, then tries
        different wrap counts to find the best match. This is more robust than
        heuristic-based approaches and can reliably detect both wrap-around and
        device resets.

        Parameters
        ----------
        raw_tick : int
            Raw tick value from device (wrapping counter) in milliseconds
        current_host_time : float
            Current host time in seconds (e.g., time.time())

        Returns
        -------
        int
            Unwrapped tick value (monotonically increasing) in milliseconds

        Notes
        -----
        Algorithm:
        1. First call establishes reference point (host time, device tick)
        2. For subsequent calls:
           - Calculate elapsed host time
           - Predict expected device tick based on elapsed time
           - Try wrap counts to find which makes actual tick closest to expected
           - If no wrap count produces reasonable match → device reset

        Assumes device clock drift is < 1000 ppm (±86.4 seconds per day).
        """
        # First call - establish reference point
        if self._reference_host_time is None:
            self._reference_host_time = current_host_time
            self._reference_device_tick_unwrapped = raw_tick
            return raw_tick

        # Calculate expected device tick based on elapsed host time
        elapsed_host = current_host_time - self._reference_host_time
        elapsed_host_ms = int(elapsed_host * 1000)
        expected_tick_unwrapped = self._reference_device_tick_unwrapped + elapsed_host_ms

        # Drift tolerance: 1% (10,000 ppm) + 200ms base
        # 1% handles RC oscillators, temperature variation, and NTP adjustments
        # The base 200ms accounts for jitter and initial sync uncertainty
        # This is intentionally lenient since we're detecting resets, not measuring drift
        drift_tolerance_ms = int(elapsed_host * 10) + 200

        # Calculate wrap count
        # We want: wrap_count * _ticks_period + raw_tick ≈ expected_tick_unwrapped
        # Solving: wrap_count ≈ (expected_tick_unwrapped - raw_tick) / _ticks_period
        best_wrap = max(0, round((expected_tick_unwrapped - raw_tick) / self._ticks_period))
        candidate_unwrapped = best_wrap * self._ticks_period + raw_tick
        candidate_diff = abs(candidate_unwrapped - expected_tick_unwrapped)

        # If best match exceeds drift tolerance → device reset detected
        if candidate_diff > drift_tolerance_ms:
            raise DeviceResetDetected(
                f"Device reset detected: drift {candidate_diff}ms exceeds "
                f"tolerance {drift_tolerance_ms}ms (elapsed {elapsed_host:.1f}s)"
            )

        # Normal operation: return unwrapped tick value
        return best_wrap * self._ticks_period + raw_tick

    def update_offset(self, device_time_ms: int, host_time_mid: float) -> None:
        """Update time offset using time-based unwrapping.

        Parameters
        ----------
        device_time_ms : int
            Raw device tick value in milliseconds; may have wrapped/overflowed.
        host_time_mid : float
            Host mid-point time in seconds (average of request and response times)

        Notes
        -----
        Wrap-around is automatically handled by unwrap_tick() using time-based
        prediction. Device resets are detected via DeviceResetDetected exception,
        which triggers re-establishment of reference points.
        """
        # Unwrap the device tick value using time-based prediction
        try:
            device_tick_unwrapped = self.unwrap_tick(device_time_ms, host_time_mid)
        except DeviceResetDetected:
            # Device reset detected - reset all tracking state then re-establish reference
            self.reset()
            self._reference_host_time = host_time_mid
            self._reference_device_tick_unwrapped = device_time_ms
            # Use raw tick as unwrapped value after reset
            device_tick_unwrapped = device_time_ms

        device_time = device_tick_unwrapped / 1000  # Convert to seconds

        # Calculate new offset
        new_offset = device_time - host_time_mid

        # First-time initialization
        if self.time_offset is None:
            self.time_offset = new_offset
            return

        # Normal operation - exponential moving average
        # Note: After a reset, offset may jump significantly, which is expected
        self.time_offset = (1 - self.alpha) * self.time_offset + self.alpha * new_offset

    def reset(self) -> None:
        """Reset wrap tracking state (for device reconnection)."""
        self._reference_host_time = None
        self._reference_device_tick_unwrapped = None


_method_metadata_counter = itertools.count()


@define
class MethodMetadata:
    """Metadata for executer-decorated Device methods."""

    executer: Callable
    kwargs: dict
    autoinit: bool = False  # Only applies to ``SetupExecuter``.
    implementation: Optional[str] = None

    id: int = field(
        factory=lambda: next(_method_metadata_counter), init=False
    )  # monotonically increasing global identifier.


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
