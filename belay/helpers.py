import secrets
import string
import sys
from functools import lru_cache, partial, wraps

from . import snippets

if sys.version_info < (3, 9, 0):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

_python_identifier_chars = string.ascii_uppercase + string.ascii_lowercase + string.digits


def wraps_partial(f, *args, **kwargs):
    """Wrap and partial of a function."""
    return wraps(f)(partial(f, *args, **kwargs))


def random_python_identifier(n=16):
    return "_" + "".join(secrets.choice(_python_identifier_chars) for _ in range(n))


@lru_cache
def read_snippet(name):
    resource = f"{name}.py"
    return importlib_resources.files(snippets).joinpath(resource).read_text()
