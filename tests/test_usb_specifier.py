from dataclasses import dataclass
from typing import Optional

import pytest

from belay import UsbSpecifier
from belay.exceptions import DeviceNotFoundError


@dataclass
class ListPortInfo:
    device: str
    name: str
    description: str = "n/a"
    hwid: str = "n/a"
    vid: Optional[int] = None
    pid: Optional[int] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    interface: Optional[str] = None


@pytest.fixture
def mock_comports(mocker):
    mock_comports = mocker.patch(
        "belay.usb_specifier.comports",
        return_value=iter(
            [
                ListPortInfo(
                    device="/dev/ttyUSB0",
                    name="ttyUSB0",
                    pid=10,
                    vid=20,
                    manufacturer="Belay Industries",
                    serial_number="abc123",
                ),
                ListPortInfo(
                    device="/dev/ttyUSB1",
                    name="ttyUSB1",
                    pid=11,
                    vid=21,
                    manufacturer="Belay Industries",
                    serial_number="xyz987",
                ),
            ]
        ),
    )
    return mock_comports


def test_usb_specifier_serial_number_only(mock_comports):
    spec = UsbSpecifier(serial_number="abc123")
    assert spec.to_port() == "/dev/ttyUSB0"


def test_usb_specifier_no_matches(mock_comports):
    with pytest.raises(DeviceNotFoundError):
        UsbSpecifier(manufacturer="Foo").to_port()


def test_usb_specifier_multiple_matches(mock_comports):
    with pytest.raises(DeviceNotFoundError):
        UsbSpecifier(manufacturer="Belay Industries").to_port()
