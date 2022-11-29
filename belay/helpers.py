import importlib.resources as pkg_resources
import secrets
import string
from functools import lru_cache, partial, wraps

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
    return pkg_resources.read_text(snippets, f"{name}.py")
