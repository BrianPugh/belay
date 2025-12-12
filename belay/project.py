import functools
import platform
from pathlib import Path
from typing import Callable, Optional, TypeVar, Union, overload

import tomli

from belay.packagemanager import BelayConfig, Group

F = TypeVar("F", bound=Callable)


class ProjectCache:
    """Decorator that caches functions and supports bulk cache clearing.

    Use this instead of ``@lru_cache`` for project config functions
    that need to be invalidated when pyproject.toml changes.
    """

    def __init__(self) -> None:
        self._cached_functions: list[functools._lru_cache_wrapper] = []

    @overload
    def __call__(self, func: F) -> F: ...

    @overload
    def __call__(self, func: None = None) -> "ProjectCache": ...

    def __call__(self, func: Optional[F] = None) -> Union[F, "ProjectCache"]:
        """Decorate a function with LRU caching and register it."""
        if func is None:  # Called as @project_cache()
            return self
        # Called as @project_cache
        cached_func = functools.lru_cache(func)
        self._cached_functions.append(cached_func)
        return cached_func  # type: ignore[return-value]

    def clear(self) -> None:
        """Clear all registered caches."""
        for func in self._cached_functions:
            func.cache_clear()


project_cache = ProjectCache()


@project_cache
def find_pyproject() -> Path:
    path = Path("pyproject.toml").absolute()

    for parent in path.parents:
        candidate = parent / path.name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f'Cannot find a pyproject.toml in the current directory "{Path().absolute()}" or any parent directory.'
    )


@project_cache
def find_project_folder() -> Path:
    return find_pyproject().parent


@project_cache
def find_belay_folder() -> Path:
    return find_project_folder() / ".belay"


@project_cache
def find_dependencies_folder() -> Path:
    config = load_pyproject()
    return find_project_folder() / config.dependencies_path


@project_cache
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


@project_cache
def find_cache_dependencies_folder() -> Path:
    return find_cache_folder() / "dependencies"


@project_cache
def load_toml(path: Union[str, Path]) -> dict:
    path = Path(path)
    with path.open("rb") as f:
        toml = tomli.load(f)

    try:
        toml = toml["tool"]["belay"]
    except KeyError:
        return {}

    return toml


@project_cache
def load_pyproject() -> BelayConfig:
    """Load the pyproject TOML file."""
    pyproject_path = find_pyproject()
    belay_data = load_toml(pyproject_path)
    return BelayConfig(**belay_data)


@project_cache
def load_groups() -> list[Group]:
    config = load_pyproject()
    groups = [Group("main", dependencies=config.dependencies)]
    groups.extend(Group(name, **definition.model_dump()) for name, definition in config.group.items())
    groups.sort(key=lambda x: x.name)
    return groups
