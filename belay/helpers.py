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
