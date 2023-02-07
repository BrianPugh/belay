"""Pydantic models for validation Belay configuration.
"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, root_validator, validator


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

    @root_validator
    def main_not_in_group(cls, values):
        if "main" in values.get("group", {}):
            raise ValueError(
                'Specify "main" group dependencies under "tool.belay.dependencies", '
                'not "tool.belay.group.main.dependencies"'
            )
        return values
