"""Pydantic models for validation Belay configuration.
"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel as PydanticBaseModel
from pydantic import root_validator, validator


class BaseModel(PydanticBaseModel):
    class Config:
        allow_mutation = False


class GroupConfig(BaseModel):
    optional: bool = False
    dependencies: Dict[str, Union[List, str]] = {}  # TODO allow dict value type.

    @validator("dependencies")
    def keys_are_python_identifiers(cls, v):
        for group_name in v:
            if not group_name.isidentifier():
                raise ValueError(
                    "Dependency group name must be a valid python identifier."
                )
        return v


class BelayConfig(BaseModel):
    """Configuration schema under the ``tool.belay`` section of ``pyproject.toml``."""

    name: Optional[str] = None
    dependencies: Dict = {}  # "main" dependencies
    group: Dict[str, GroupConfig] = {}  # Other dependencies

    @validator("group")
    def main_not_in_group(cls, v):
        if "main" in v:
            raise ValueError(
                'Specify "main" group dependencies under "tool.belay.dependencies", '
                'not "tool.belay.group.main.dependencies"'
            )
        return v
