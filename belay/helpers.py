import importlib.resources as importlib_resources
import secrets
import string
import sys
from functools import lru_cache, partial, wraps
from pathlib import Path
from typing import Optional

from . import nativemodule_fnv1a32, snippets

_python_identifier_chars = string.ascii_uppercase + string.ascii_lowercase + string.digits


def wraps_partial(f, *args, **kwargs):
    """Wrap and partial of a function."""
    return wraps(f)(partial(f, *args, **kwargs))


def random_python_identifier(n=16):
    return "_" + "".join(secrets.choice(_python_identifier_chars) for _ in range(n))


@lru_cache
def read_snippet(name):
    resource = f"{name}.py"
    return importlib_resources.files(snippets).joinpath(resource).read_text(encoding="utf-8")


def get_fnv1a32_native_path(implementation) -> Optional[Path]:
    if implementation.name != "micropython":
        return None
    mpy_fn = f"mpy{implementation.version[0]}.{implementation.version[1]}-{implementation.arch}.mpy"
    filepath = importlib_resources.files(nativemodule_fnv1a32).joinpath(mpy_fn)
    return filepath if filepath.exists() else None


def sanitize_package_name(name: str) -> str:
    """Convert string to valid Python identifier.

    Strips file extensions (.py, .mpy) and replaces hyphens with underscores.

    Parameters
    ----------
    name
        Raw name (e.g., from a URI path component).

    Returns
    -------
    str
        Sanitized package name suitable as a Python identifier.

    Raises
    ------
    ValueError
        If name cannot be converted to a valid identifier.

    Examples
    --------
    >>> sanitize_package_name("my-package")
    'my_package'
    >>> sanitize_package_name("module.py")
    'module'
    >>> sanitize_package_name("sensor.mpy")
    'sensor'
    """
    # Remove common file extensions
    for ext in (".py", ".mpy"):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    # Replace hyphens with underscores
    name = name.replace("-", "_")
    # Validate result
    if not name.isidentifier():
        raise ValueError(f"Cannot convert '{name}' to valid package name.")
    return name
