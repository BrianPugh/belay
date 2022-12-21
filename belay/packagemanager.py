import ast
import shutil
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from urllib.parse import urlparse

import httpx
from rich.console import Console


class NonMatchingURL(Exception):
    pass


@dataclass
class GroupConfig:
    """Schema and store of a group defined in ``pyproject.toml``.

    Don't put any methods in here, they go in ``Group``.
    This class is primarily for namespacing and validation.
    """

    name: str
    optional: bool = False
    dependencies: Dict[str, str] = field(default_factory=dict)


@dataclass
class Group:
    """Represents a group defined in ``pyproject.toml``."""

    def __init__(self, *args, **kwargs):
        from belay.project import find_dependencies_folder

        self.config = GroupConfig(*args, **kwargs)

        self.folder = find_dependencies_folder() / self.config.name

        if self.config.optional:
            raise NotImplementedError("Optional groups not implemented yet.")

    def clean(self):
        folder = self.folder
        dependencies = set(self.config.dependencies)
        existing_deps = []

        if not folder.exists():
            return

        existing_deps.extend(folder.rglob("*.py"))

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
            for pkg_name in packages:
                dep = self.config.dependencies[pkg_name]
                if isinstance(dep, str):
                    dep = {"path": dep}
                elif not isinstance(dep, dict):
                    raise ValueError(f"Invalid value for key {pkg_name}.")

                log(f"{pkg_name}: Updating...")

                url = _process_url(dep["path"])
                ext = Path(url).suffix

                # Single file
                dst = self.folder / (pkg_name + ext)
                dst.parent.mkdir(parents=True, exist_ok=True)

                new_code = _get_text(url)

                if ext == ".py":
                    ast.parse(new_code)  # Check for valid python code

                try:
                    old_code = dst.read_text()
                except FileNotFoundError:
                    old_code = ""

                if new_code == old_code:
                    log(f"{pkg_name}: No changes detected.")
                else:
                    log(f"[bold green]{pkg_name}: Updated.")
                    dst.write_text(new_code)


def _strip_www(url: str):
    if url.startswith("www."):
        url = url[4:]
    return url


def _process_url_github(url: str):
    """Transforms github-like url into githubusercontent."""
    url = str(url)
    parsed = urlparse(url)
    netloc = _strip_www(parsed.netloc)
    if netloc == "github.com":
        # Transform to raw.githubusercontent
        _, user, project, mode, branch, *path = parsed.path.split("/")
        return f"https://raw.githubusercontent.com/{user}/{project}/{branch}/{'/'.join(path)}"
    elif netloc == "raw.githubusercontent.com":
        return f"https://raw.githubusercontent.com{parsed.path}"
    else:
        # TODO: Try and be a little helpful if url contains github.com
        raise NonMatchingURL


def _process_url(url: str):
    parsers = [
        _process_url_github,
    ]
    for parser in parsers:
        try:
            return parser(url)
        except NonMatchingURL:
            pass

    # Unmodified URL
    return url


def _get_text(url: Union[str, Path]):
    url = str(url)
    if url.startswith(("https://", "http://")):
        res = httpx.get(url)
        res.raise_for_status()
        return res.text
    else:
        # Assume local file
        return Path(url).read_text()
