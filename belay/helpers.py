import importlib.resources
import secrets
import string
from functools import lru_cache, partial, wraps
from typing import List

from serial.tools import list_ports

from . import snippets

_python_identifier_chars = (
    string.ascii_uppercase + string.ascii_lowercase + string.digits
)


def wraps_partial(f, *args, **kwargs):
    """Wrap and partial of a function."""
    return wraps(f)(partial(f, *args, **kwargs))


def random_python_identifier(n=16):
    return "_" + "".join(secrets.choice(_python_identifier_chars) for _ in range(n))


@lru_cache
def read_snippet(name):
    resource = f"{name}.py"
    return importlib.resources.files(snippets).joinpath(resource).read_text()


def list_devices() -> List[str]:
    """Lists available device ports.

    For example::

        ['/dev/cu.usbmodem1143401', '/dev/cu.usbmodem113101']

    Returns
    -------
    list[str]
        Available devices identifiers.
    """
    return [port.device for port in list_ports.comports()]
