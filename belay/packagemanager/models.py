"""Pydantic models for validation Belay configuration.
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, field_validator


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(frozen=True)


class DependencySourceConfig(BaseModel):
    uri: str
    develop: bool = False  # If true, local dependency is in "editable" mode.

    rename_to_init: bool = False


DependencyList = list[DependencySourceConfig]


def _dependencies_name_validator(dependencies) -> dict:
    for group_name in dependencies:
        if not group_name.isidentifier():
            raise ValueError("Dependency group name must be a valid python identifier.")
    return dependencies


def _dependencies_preprocessor(dependencies) -> dict[str, list[dict]]:
    """Preprocess various dependencies based on dtype.

    * ``str`` -> single dependency that may get renamed to __init__.py, if appropriate.
    * ``list`` -> list of dependencies. If an element is a str, it will not
      get renamed to __init__.py.
    * ``dict`` -> full dependency specification.
    """
    out = {}
    for group_name, group_value in dependencies.items():
        if isinstance(group_value, str):
            group_value = [
                {
                    "uri": group_value,
                    "rename_to_init": True,
                }
            ]
        elif isinstance(group_value, list):
            group_value_out = []
            for elem in group_value:
                if isinstance(elem, str):
                    group_value_out.append(
                        {
                            "uri": elem,
                        }
                    )
                elif isinstance(elem, list):
                    raise TypeError("Cannot have double nested lists in dependency specification.")
                elif isinstance(elem, (dict, DependencySourceConfig)):
                    group_value_out.append(elem)
                else:
                    raise NotImplementedError
            group_value = group_value_out
        elif isinstance(group_value, dict):
            group_value = group_value.copy()
            group_value.setdefault("rename_to_init", True)
            group_value = [group_value]
        elif isinstance(group_value, DependencySourceConfig):
            # Nothing to do
            pass
        else:
            raise TypeError

        out[group_name] = group_value

    return out


def walk_dependencies(packages: dict):
    """Walks over all package/dependency pairs.

    Yields
    ------
    tuple
        (package_name, dependency)
    """
    for package_name, dependencies in packages.items():
        for dependency in dependencies:
            yield package_name, dependency


class GroupConfig(BaseModel):
    optional: bool = False
    dependencies: dict[str, DependencyList] = {}

    ##############
    # VALIDATORS #
    ##############
    @field_validator("dependencies", mode="before")
    @classmethod
    def _v_dependencies_preprocessor(cls, v):
        return _dependencies_preprocessor(v)

    @field_validator("dependencies")
    @classmethod
    def _v_dependencies_names(cls, v):
        return _dependencies_name_validator(v)

    @field_validator("dependencies")
    @classmethod
    def max_1_rename_to_init(cls, packages: dict):
        rename_to_init_count = {}
        for package_name, dependency in walk_dependencies(packages):
            rename_to_init_count.setdefault(package_name, 0)
            rename_to_init_count[package_name] += dependency.rename_to_init
            if rename_to_init_count[package_name] > 1:
                raise ValueError(f'{package_name} has more than 1 dependency marked with "rename_to_init".')
        return packages


class BelayConfig(BaseModel):
    """Configuration schema under the ``tool.belay`` section of ``pyproject.toml``."""

    # Name/Folder of project's primary micropython code.
    name: Optional[str] = None

    # Items in project directory to ignore.
    ignore: Optional[list] = []

    # "main" dependencies
    dependencies: dict[str, DependencyList] = {}

    # Path to where dependency groups should be stored relative to project's root.
    dependencies_path: Path = Path(".belay/dependencies")

    # Other dependencies
    group: dict[str, GroupConfig] = {}

    ##############
    # VALIDATORS #
    ##############
    @field_validator("dependencies", mode="before")
    @classmethod
    def _v_dependencies_preprocessor(cls, v):
        return _dependencies_preprocessor(v)

    @field_validator("dependencies")
    @classmethod
    def _v_dependencies_names(cls, v):
        return _dependencies_name_validator(v)

    @field_validator("group")
    @classmethod
    def main_not_in_group(cls, v):
        if "main" in v:
            raise ValueError(
                'Specify "main" group dependencies under "tool.belay.dependencies", '
                'not "tool.belay.group.main.dependencies"'
            )
        return v
