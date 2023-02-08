"""Pydantic models for validation Belay configuration.
"""

from functools import partial
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel as PydanticBaseModel
from pydantic import root_validator, validator

validator_reuse = partial(validator, allow_reuse=True)


def _dependencies_validator(dependencies):
    for group_name, _group_value in dependencies.items():
        if not group_name.isidentifier():
            raise ValueError("Dependency group name must be a valid python identifier.")
        # TODO: validate and probably cast group_value into a DependencyConfig type.
    return dependencies


class BaseModel(PydanticBaseModel):
    class Config:
        allow_mutation = False


class DependencyConfig(BaseModel):
    # TODO
    pass


class GroupConfig(BaseModel):
    optional: bool = False
    dependencies: Dict[str, Union[List, str]] = {}  # TODO allow dict value type.

    ##############
    # VALIDATORS #
    ##############
    _v_dependencies = validator_reuse("dependencies")(_dependencies_validator)


class BelayConfig(BaseModel):
    """Configuration schema under the ``tool.belay`` section of ``pyproject.toml``."""

    # Name/Folder of project's primary micropython code.
    name: Optional[str] = None

    # "main" dependencies
    dependencies: Dict[str, Union[List, str]] = {}  # TODO allow dict value type.

    # Path to where dependency groups should be stored relative to project's root.
    dependencies_path: Path = Path(".belay/dependencies")

    # Other dependencies
    group: Dict[str, GroupConfig] = {}

    ##############
    # VALIDATORS #
    ##############
    _v_dependencies = validator_reuse("dependencies")(_dependencies_validator)

    @validator("group")
    def main_not_in_group(cls, v):
        if "main" in v:
            raise ValueError(
                'Specify "main" group dependencies under "tool.belay.dependencies", '
                'not "tool.belay.group.main.dependencies"'
            )
        return v
