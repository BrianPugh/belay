import ast
import shutil
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from belay.packagemanager.downloaders import download_uri
from belay.packagemanager.models import (
    DependencySourceConfig,
    GroupConfig,
    walk_dependencies,
)
from belay.packagemanager.sync import sync
from belay.typing import PathType


class Group:
    """Represents a group defined in ``pyproject.toml``."""

    def __init__(self, name: str, **kwargs):
        from belay.project import find_dependencies_folder

        self.name = name
        self.config = GroupConfig(**kwargs)
        self.folder = find_dependencies_folder() / self.name

    def __eq__(self, other):
        if not isinstance(other, Group):
            return False
        return self.config.__dict__ == other.config.__dict__

    def __repr__(self):
        kws = [f"{key}={value!r}" for key, value in self.config.__dict__.items()]
        return f"{type(self).__name__}({', '.join(kws)})"

    @property
    def optional(self) -> bool:
        return self.config.optional

    @property
    def dependencies(self):
        return self.config.dependencies

    def clean(self):
        """Delete any dependency module not specified in ``self.config.dependencies``."""
        dependencies = set(self.dependencies)

        if not self.folder.exists():
            return

        for existing_dep in self.folder.glob("*"):
            if existing_dep.name in dependencies:
                continue

            if existing_dep.is_dir():
                shutil.rmtree(existing_dep)
            else:
                existing_dep.unlink()

    def copy_to(self, dst: PathType) -> None:
        """Copy Dependencies folder to destination directory.

        Used to stage files for sync/installation.
        """
        dst = Path(dst)

        if self.folder.exists():
            # Bulk copy over the group contents
            shutil.copytree(self.folder, dst, dirs_exist_ok=True)

        # Copy over any (& overwrite) any dependencies in ``develop`` mode.
        for package_name, dependency in _walk_develop_dependencies(self.dependencies):
            dst_package_folder = dst / package_name
            dst_package_folder.mkdir(parents=True, exist_ok=True)
            _download_and_verify_dependency(dst_package_folder, dependency)

    def _download_package(self, package_name) -> bool:
        """Download a single package.

        Returns
        -------
        changed: bool
            If existing files have changed after download.
        """
        local_folder = self.folder / package_name
        local_folder.mkdir(exist_ok=True, parents=True)

        dependencies = self.dependencies[package_name]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            for dependency in dependencies:
                _download_and_verify_dependency(tmp_dir, dependency)
            changed = sync(tmp_dir, local_folder)

        return changed

    def download(
        self,
        packages: Optional[List[str]] = None,
        console: Optional[Console] = None,
    ) -> None:
        """Download dependencies.

        Parameters
        ----------
        packages: Optional[List[str]]
            Only download these package.
        console: Optional[Console]
            Print progress out to console.
        """
        if packages is None:
            # Update all packages
            packages = list(self.dependencies.keys())

        if not packages:
            return

        cm = console.status("[bold green]Updating Dependencies") if console else nullcontext()

        def log(*args, **kwargs):
            if console:
                console.print(*args, **kwargs)

        with cm:
            for package_name in packages:
                log(f"  • {package_name}: Updating...", end=" ")
                changed = self._download_package(package_name)
                if changed:
                    log(f"  • [bold green]{package_name}: Updated.")
                else:
                    log(f"  • {package_name}: No changes detected.")


def _verify_files(path: PathType):
    """Sanity checks downloaded files.

    Performs the following checks:

    * ".py" files are valid python code.

    Parameters
    ----------
    path
        Either a single file or a folder.
    """
    path = Path(path)

    gen = path.rglob("*") if path.is_dir() else [path]

    for f in gen:
        if f.suffix == ".py":
            code = f.read_text()
            ast.parse(code)


def _walk_develop_dependencies(packages: dict):
    for package_name, dependency in walk_dependencies(packages):
        if dependency.develop:
            yield package_name, dependency


def _download_and_verify_dependency(download_folder: PathType, dependency: DependencySourceConfig):
    """Download and verify a dependency.

    Parameters
    ----------
    download_folder
        Destination directory for downloaded file(s).
    """
    out = download_uri(download_folder, dependency.uri)
    if dependency.rename_to_init and out.is_file() and out.suffix in (".py", ".mpy"):
        out = out.rename(out.parent / f"__init__{out.suffix}")

    _verify_files(out)
