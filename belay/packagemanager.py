import ast
import shutil
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from urllib.parse import urlparse

import httpx
from autoregistry import Registry
from rich.console import Console


class NonMatchingURI(Exception):
    pass


uri_processors = Registry()


@dataclass
class GroupConfig:
    """Schema and store of a group defined in ``pyproject.toml``.

    Don't put any methods in here, they go in ``Group``.
    This class is primarily for namespacing and validation.
    """

    name: str
    optional: bool = False
    dependencies: Dict[str, str] = field(default_factory=dict)


class Group:
    """Represents a group defined in ``pyproject.toml``."""

    def __init__(self, *args, **kwargs):
        from belay.project import find_dependencies_folder

        self.config = GroupConfig(*args, **kwargs)

        self.folder = find_dependencies_folder() / self.config.name

        if self.config.optional:
            raise NotImplementedError("Optional groups not implemented yet.")

    def __eq__(self, other):
        if not isinstance(other, Group):
            return False
        return self.config.__dict__ == other.config.__dict__

    def __repr__(self):
        kws = [f"{key}={value!r}" for key, value in self.config.__dict__.items()]
        return f"{type(self).__name__}({', '.join(kws)})"

    def clean(self):
        """Delete any dependency module not specified in ``self.config.dependencies``."""
        dependencies = set(self.config.dependencies)
        existing_deps = []

        if not self.folder.exists():
            return

        existing_deps.extend(self.folder.glob("*"))

        for existing_dep in existing_deps:
            if existing_dep.stem in dependencies:
                continue
            existing_dep.unlink()

    def copy_to(self, dst):
        """Copy Dependencies folder to destination directory."""
        if self.folder.exists():
            shutil.copytree(self.folder, dst, dirs_exist_ok=True)

    def download(
        self,
        packages: Optional[List[str]] = None,
        console: Optional[Console] = None,
    ):
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
            packages = list(self.config.dependencies.keys())

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
                dep_src = self.config.dependencies[package_name]
                if isinstance(dep_src, str):
                    dep_src = {"path": dep_src}
                elif not isinstance(dep_src, dict):
                    raise ValueError(f"Invalid value for key {package_name}.")

                log(f"{package_name}: Updating...")

                uri = _process_uri(dep_src["path"])
                ext = Path(uri).suffix

                # Single file
                dst = self.folder / (package_name + ext)
                dst.parent.mkdir(parents=True, exist_ok=True)

                new_code = _get_text(uri)

                if ext == ".py":
                    ast.parse(new_code)  # Check for valid python code

                try:
                    old_code = dst.read_text()
                except FileNotFoundError:
                    old_code = ""

                if new_code == old_code:
                    log(f"{package_name}: No changes detected.")
                else:
                    log(f"[bold green]{package_name}: Updated.")
                    dst.write_text(new_code)


def _strip_www(uri: str):
    if uri.startswith("www."):
        uri = uri[4:]
    return uri


@uri_processors
def _process_uri_github(uri: str):
    """Transforms github-like uri into githubusercontent."""
    uri = str(uri)
    parsed = urlparse(uri)
    netloc = _strip_www(parsed.netloc)
    if netloc == "github.com":
        # Transform to raw.githubusercontent
        _, user, project, mode, branch, *path = parsed.path.split("/")
        return f"https://raw.githubusercontent.com/{user}/{project}/{branch}/{'/'.join(path)}"
    elif netloc == "raw.githubusercontent.com":
        return f"https://raw.githubusercontent.com{parsed.path}"
    else:
        # TODO: Try and be a little helpful if uri contains github.com
        raise NonMatchingURI


def _process_uri(uri: str):
    for processor in uri_processors.values():
        try:
            return processor(uri)
        except NonMatchingURI:
            pass

    # Unmodified URI
    return uri


def _get_text(uri: Union[str, Path]):
    uri = str(uri)
    if uri.startswith(("https://", "http://")):
        res = httpx.get(uri)
        res.raise_for_status()
        return res.text
    else:
        # Assume local file
        return Path(uri).read_text()
