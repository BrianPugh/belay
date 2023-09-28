import pydantic
import pytest

from belay.packagemanager import GroupConfig

try:
    from pydantic.v1.error_wrappers import ValidationError
except ImportError:
    from pydantic import ValidationError


def test_group_config_multiple_rename_to_init():
    dependencies = {
        "package": [
            {"uri": "foo", "rename_to_init": True},
            {"uri": "bar", "rename_to_init": True},
        ]
    }
    with pytest.raises(ValidationError):
        GroupConfig(dependencies=dependencies)
