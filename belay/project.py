from functools import lru_cache
from pathlib import Path
from typing import List, Union

import tomli

from belay.exceptions import ConfigError
from belay.packagemanager import Group


@lru_cache
def find_pyproject() -> Path:
    path = Path("pyproject.toml").absolute()

    for parent in path.parents:
        candidate = parent / path.name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f'Cannot find a pyproject.toml in the current directory "{Path().absolute()}" or any parent directory.'
    )


@lru_cache
def find_project_folder() -> Path:
    return find_pyproject().parent


@lru_cache
def find_belay_folder() -> Path:
    return find_project_folder() / ".belay"


@lru_cache
def find_dependencies_folder() -> Path:
    return find_belay_folder() / "dependencies"


@lru_cache
def load_toml(path: Union[str, Path]) -> dict:
    path = Path(path)
    with path.open("rb") as f:
        toml = tomli.load(f)

    try:
        toml = toml["tool"]["belay"]
    except KeyError:
        return {}

    return toml


@lru_cache
def load_pyproject() -> dict:
    """Load the pyproject TOML file."""
    pyproject_path = find_pyproject()
    return load_toml(pyproject_path)


@lru_cache
def load_groups() -> List[Group]:
    config = load_pyproject()
    groups_definitions = config.get("group", {})
    if "main" in groups_definitions:
        raise ConfigError(
            'Specify "main" group dependencies under "tool.belay.dependencies", '
            'not "tool.belay.group.main.dependencies"'
        )
    if "dependencies" in config:
        groups_definitions["main"] = {"dependencies": config["dependencies"]}

    groups = [
        Group(name, **definition) for name, definition in groups_definitions.items()
    ]
    groups.sort(key=lambda x: x.config.name)

    return groups
