import pydantic
import pytest
from pydantic import ValidationError

from belay.packagemanager import GroupConfig


def test_group_config_multiple_rename_to_init():
    dependencies = {
        "package": [
            {"uri": "foo", "rename_to_init": True},
            {"uri": "bar", "rename_to_init": True},
        ]
    }
    with pytest.raises(ValidationError):
        GroupConfig(dependencies=dependencies)
