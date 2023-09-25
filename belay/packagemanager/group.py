from attrs import frozen, field
import ast
import shutil
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import List, Optional, Dict

from rich.console import Console

from belay.packagemanager.downloaders import download_uri
from belay.packagemanager.sync import sync
from belay.typing import PathType


@frozen
class DependencySource:
    uri: str

    # If true, local dependency is in "editable" mode.
    develop: bool = False

    # Rename the downloaded file to `__init__.py`.
    # Intended for single-file libraries.
    rename_to_init: bool = False

    def download_and_verify(self, download_folder):
        """Download and verify a dependency.

        Parameters
        ----------
        download_folder
            Destination directory for downloaded file(s).
        """
        out = download_uri(download_folder, self.uri)
        if self.rename_to_init and out.is_file() and out.suffix == ".py":
            out = out.rename(out.parent / "__init__.py")

        _verify_files(out)


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


def walk_dependencies(packages: Dict[str, List[DependencySource]]):
    """Walks over all package/dependency pairs.

    Yields
    ------
    tuple
        (package_name, dependency)
    """
    for package_name, dependencies in packages.items():
        for dependency in dependencies:
            yield package_name, dependency


def walk_develop_dependencies(packages: Dict[str, List[DependencySource]]):
    for package_name, dependency in walk_dependencies(packages):
        if dependency.develop:
            yield package_name, dependency


@frozen
class Group:
    """Represents a group defined in ``pyproject.toml``."""
    name: str
    optional: bool = False
    dependencies: Dict[str, List[DependencySource]] = field(factory=dict)

    folder: Path = field(init=False)

    @dependencies.validator  # pyright: ignore[reportGeneralTypeIssues]
    def _validator_max_1_rename_to_init(self, _, packages):
        rename_to_init_count = {}
        for package_name, dependency in walk_dependencies(packages):
            rename_to_init_count.setdefault(package_name, 0)
            rename_to_init_count[package_name] += dependency.rename_to_init
            if rename_to_init_count[package_name] > 1:
                raise ValueError(f'{package_name} has more than 1 dependency marked with "rename_to_init".')

    def __attrs_post_init__(self):
        from belay.project import find_dependencies_folder
        # circumvent "frozen"
        object.__setattr__(self, "folder", find_dependencies_folder() / self.name)

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
        for package_name, dependency in walk_develop_dependencies(self.dependencies):
            dst_package_folder = dst / package_name
            dst_package_folder.mkdir(parents=True, exist_ok=True)
            dependency.download_and_verify(dst_package_folder)

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
                dependency.download_and_verify(tmp_dir)
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
