import os
from typing import Literal


def env_parse_bool(env_var, default_value=False):
    if env_var in os.environ:
        env_value = os.environ[env_var].lower()
        return env_value == "true" or env_value == "1"
    else:
        return default_value


class SentinelMeta(type):
    def __repr__(cls) -> str:
        return f"<{cls.__name__}>"

    def __bool__(cls) -> Literal[False]:
        return False


class Sentinel(metaclass=SentinelMeta):
    def __new__(cls):
        raise ValueError("Sentinel objects are not intended to be instantiated. Subclass instead.")
