"""Pydantic models for validation Belay configuration.
"""

import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, field_validator

from belay.packagemanager.package_json import DEFAULT_MPY_VERSION, DEFAULT_PACKAGE_INDICES

# Pattern for version-only strings (e.g., "1.0.0", "2.1", "0.5.1.2")
_VERSION_PATTERN = re.compile(r"^\d+(\.\d+)*$")

# Characters that indicate version ranges (not supported)
_VERSION_RANGE_PREFIXES = frozenset("^~><=!")


class VersionRangeNotSupportedError(ValueError):
    """Raised when a version range is specified but not supported."""


def _transform_version_uri(package_name: str, uri: str) -> str:
    """Transform version/wildcard syntax into proper URI for index lookup.

    Parameters
    ----------
    package_name
        The dependency key name (e.g., "aiohttp").
    uri
        The dependency value (e.g., "*", "1.0.0", "github:...").

    Returns
    -------
    str
        The URI to use for downloading.

    Raises
    ------
    VersionRangeNotSupportedError
        If a version range syntax is detected.

    Examples
    --------
    >>> _transform_version_uri("aiohttp", "*")
    'aiohttp'
    >>> _transform_version_uri("aiohttp", "latest")
    'aiohttp'
    >>> _transform_version_uri("requests", "1.0.0")
    'requests@1.0.0'
    >>> _transform_version_uri("pathlib", "github:user/repo")
    'github:user/repo'
    """
    if not uri:
        return uri

    # Check for version range syntax (not supported)
    if uri[0] in _VERSION_RANGE_PREFIXES:
        raise VersionRangeNotSupportedError(
            f'Version ranges are not supported: {package_name} = "{uri}". '
            f'Use "*" for latest or an exact version like "1.0.0".'
        )

    # Wildcard or "latest" -> use package name for index lookup
    if uri in ("*", "latest"):
        return package_name

    # Version string -> package_name@version
    if _VERSION_PATTERN.match(uri):
        return f"{package_name}@{uri}"

    # Otherwise, pass through unchanged (URLs, paths, mip:, github:, etc.)
    return uri


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
      Supports version/wildcard syntax: "*", "latest", or "1.0.0".
    * ``list`` -> list of dependencies. If an element is a str, it will not
      get renamed to __init__.py.
    * ``dict`` -> full dependency specification.
    """
    out = {}
    for group_name, group_value in dependencies.items():
        if isinstance(group_value, str):
            uri = _transform_version_uri(group_name, group_value)
            group_value = [
                {
                    "uri": uri,
                    "rename_to_init": True,
                }
            ]
        elif isinstance(group_value, list):
            group_value_out = []
            for elem in group_value:
                if isinstance(elem, str):
                    # List elements don't get version transformation
                    # (they're typically explicit URLs for multi-file packages)
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
            if "uri" in group_value:
                group_value["uri"] = _transform_version_uri(group_name, group_value["uri"])
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

    # MicroPython package index settings
    # MicroPython version for index package lookups.
    # Use "py" for pure Python source, or version number like "6" for compiled .mpy files.
    mpy_version: str = DEFAULT_MPY_VERSION

    # URLs of package indices for MicroPython package name lookups.
    # Indices are tried in order; first match wins.
    package_indices: list[str] = list(DEFAULT_PACKAGE_INDICES)

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

    @field_validator("mpy_version")
    @classmethod
    def validate_mpy_version(cls, v):
        """Validate mpy_version is a recognized format.

        Valid values:
        - "py": Pure Python source files
        - Numeric string (e.g., "6"): Compiled .mpy format version
        """
        if not v:
            raise ValueError("mpy_version cannot be empty")
        if v != "py" and not v.isdigit():
            raise ValueError(
                f'Invalid mpy_version: "{v}". '
                'Use "py" for pure Python or a number like "6" for compiled .mpy format.'
            )
        return v

    @field_validator("package_indices")
    @classmethod
    def validate_package_indices(cls, v):
        """Validate that package indices are well-formed URLs."""
        from urllib.parse import urlparse

        for url in v:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Invalid package index URL (must be http:// or https://): {url}")
            if not parsed.netloc:
                raise ValueError(f"Invalid package index URL (missing host): {url}")
        return v
