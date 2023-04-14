from typing import Dict, Optional

from pydantic import BaseModel, Field
from serial.tools.list_ports import comports

from .exceptions import DeviceNotFoundError, InsufficientSpecifierError


def _normalize(val):
    """Normalize ``val`` for comparison."""
    if isinstance(val, str):
        return val.casefold()
    return val


def _dict_is_subset(subset: Dict, superset: Dict) -> bool:
    """Tests if ``subset`` dictionary is a subset of ``superset`` dictionary."""
    for subset_key, subset_value in subset.items():
        try:
            superset_value = superset[subset_key]
        except KeyError:
            return False

        if _normalize(subset_value) != _normalize(superset_value):
            return False
    return True


class UsbSpecifier(BaseModel):
    """Usb port metadata."""

    vid: Optional[int] = None
    pid: Optional[int] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    location: Optional[str] = None

    device: Optional[str] = Field(None, exclude=True)

    def __repr__(self):
        return f'{self.__class__.__name__}({", ".join(f"{k}={v!r}" for k, v in self.dict().items() if v is not None)})'

    def to_port(self) -> str:
        if self.device:
            return self.device

        spec = self.dict(exclude_none=True)
        possible_matches = []

        for port_info in comports():
            if _dict_is_subset(spec, vars(port_info)):
                possible_matches.append(port_info)
        if not possible_matches:
            raise DeviceNotFoundError
        elif len(possible_matches) > 1:
            message = "Multiple potential devices found:\n" + "\n".join(
                f"    {vars(x)}" for x in possible_matches
            )
            raise InsufficientSpecifierError(message)

        return possible_matches[0].device

    def populated(self):
        return bool(self.dict(exclude_none=True))
