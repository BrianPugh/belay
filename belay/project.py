import platform
from functools import lru_cache
from pathlib import Path
from typing import List, Union

import tomli

from belay.packagemanager import BelayConfig, Group


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
    config = load_pyproject()
    return find_project_folder() / config.dependencies_path


@lru_cache
def find_cache_folder() -> Path:
    system = platform.system()
    cache_folder = Path.home()

    if system == "Windows":
        cache_folder /= "AppData/Local/belay/Cache"
    elif system == "Darwin":
        cache_folder /= "Library/Caches/belay"
    else:
        cache_folder /= ".cache/belay"

    return cache_folder.absolute()


@lru_cache
def find_cache_dependencies_folder() -> Path:
    return find_cache_folder() / "dependencies"


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
def load_pyproject() -> BelayConfig:
    """Load the pyproject TOML file."""
    pyproject_path = find_pyproject()
    belay_data = load_toml(pyproject_path)
    return BelayConfig(**belay_data)


@lru_cache
def load_groups() -> List[Group]:
    config = load_pyproject()
    groups = [Group("main", dependencies=config.dependencies)]
    groups.extend(Group(name, **definition.dict()) for name, definition in config.group.items())
    groups.sort(key=lambda x: x.name)
    return groups
