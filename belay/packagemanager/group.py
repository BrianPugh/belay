import ast
import shutil
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from belay.packagemanager.downloaders import download_uri
from belay.packagemanager.models import GroupConfig
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

    def copy_to(self, dst) -> None:
        """Copy Dependencies folder to destination directory."""
        if self.folder.exists():
            shutil.copytree(self.folder, dst, dirs_exist_ok=True)

    def _download_package(self, package_name) -> bool:
        local_folder = self.folder / package_name
        local_folder.mkdir(exist_ok=True, parents=True)

        dependencies = self.dependencies[package_name]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            for src in dependencies:
                out = download_uri(tmp_dir, src.uri)

                if src.rename_to_init and out.is_file() and out.suffix == ".py":
                    out.rename(out.parent / "__init__.py")

            _verify_files(tmp_dir)
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

        if console:
            cm = console.status("[bold green]Updating Dependencies")
        else:
            cm = nullcontext()

        def log(*args, **kwargs):
            if console:
                console.log(*args, **kwargs)

        with cm:
            for package_name in packages:
                log(f"{package_name}: Updating...")
                changed = self._download_package(package_name)
                if changed:
                    log(f"[bold green]{package_name}: Updated.")
                else:
                    log(f"{package_name}: No changes detected.")


def _verify_files(folder: PathType):
    """Sanity checks downloaded files.

    Currently just checks if ".py" files are valid python code.
    """
    folder = Path(folder)
    for f in folder.rglob("*"):
        if f.suffix == ".py":
            code = f.read_text()
            ast.parse(code)
